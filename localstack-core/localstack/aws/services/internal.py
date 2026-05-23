"""Module for localstack internal resources, such as health, graph, or _localstack/cloudformation/deploy."""

import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import time
import uuid
from collections import defaultdict
from datetime import datetime

from plux import PluginManager

from localstack.platform import config, constants
from localstack.platform.deprecations import deprecated_endpoint
from localstack.platform.http import Request, Resource, Response, Router
from localstack.platform.http.dispatcher import handler_dispatcher
from localstack.platform.runtime.legacy import signal_supervisor_restart
from localstack.utils.analytics.metadata import (
    get_client_metadata,
    get_localstack_edition,
    is_license_activated,
)
from localstack.utils.collections import merge_recursive
from localstack.utils.functions import call_safe
from localstack.utils.numbers import is_number
from localstack.utils.objects import singleton_factory

LOG = logging.getLogger(__name__)

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"]


class DeprecatedResource:
    """
    Resource class which wraps a given resource in the deprecated_endpoint (i.e. logs deprecation warnings on every
    invocation).
    """

    def __init__(self, resource, previous_path: str, deprecation_version: str, new_path: str):
        for http_method in HTTP_METHODS:
            fn_name = f"on_{http_method.lower()}"
            fn = getattr(resource, fn_name, None)
            if fn:
                wrapped = deprecated_endpoint(
                    fn,
                    previous_path=previous_path,
                    deprecation_version=deprecation_version,
                    new_path=new_path,
                )
                setattr(self, fn_name, wrapped)


class HealthResource:
    """
    Resource for the LocalStack /health endpoint. It provides access to the service states and other components of
    localstack. We support arbitrary data to be put into the health state to support things like the
    run_startup_scripts function in docker-entrypoint.sh which sets the status of the init scripts feature.
    """

    def __init__(self, service_manager) -> None:
        super().__init__()
        self.service_manager = service_manager
        self.state = {}

    def on_post(self, request: Request):
        data = request.get_json(True, True)
        if not data:
            return Response("invalid request", 400)

        # backdoor API to support restarting the instance
        if data.get("action") == "restart":
            signal_supervisor_restart()
        elif data.get("action") == "kill":
            from localstack.platform.runtime import get_current_runtime

            get_current_runtime().exit(0)

        return Response("ok", 200)

    def on_get(self, request: Request):
        path = request.path

        reload = "reload" in path

        # get service state
        if reload:
            self.service_manager.check_all()
        services = {
            service: state.value for service, state in self.service_manager.get_states().items()
        }

        # build state dict from internal state and merge into it the service states
        result = dict(self.state)
        result = merge_recursive({"services": services}, result)
        result["edition"] = get_localstack_edition()
        result["version"] = constants.VERSION
        return result

    def on_head(self, request: Request):
        return Response("ok", 200)

    def on_put(self, request: Request):
        data = request.get_json(True, True) or {}

        # keys like "features:initScripts" should be interpreted as ['features']['initScripts']
        state = defaultdict(dict)
        for k, v in data.items():
            if ":" in k:
                path = k.split(":")
            else:
                path = [k]

            d = state
            for p in path[:-1]:
                d = state[p]
            d[path[-1]] = v

        self.state = merge_recursive(state, self.state, overwrite=True)
        return {"status": "OK"}


class InfoResource:
    """
    Resource that is exposed to /_localstack/info and used to get generalized information about the current
    localstack instance.
    """

    def on_get(self, request):
        return self.get_info_data()

    @staticmethod
    def get_info_data() -> dict:
        client_metadata = get_client_metadata()
        uptime = int(time.time() - config.load_start_time)

        return {
            "version": client_metadata.version,
            "edition": get_localstack_edition(),
            "is_license_activated": is_license_activated(),
            "session_id": client_metadata.session_id,
            "machine_id": client_metadata.machine_id,
            "system": client_metadata.system,
            "is_docker": client_metadata.is_docker,
            "server_time_utc": datetime.utcnow().isoformat(timespec="seconds"),
            "uptime": uptime,
        }


class UsageResource:
    def on_get(self, request):
        from localstack.utils import diagnose

        return call_safe(diagnose.get_usage) or {}


class DiagnoseResource:
    def on_get(self, request):
        from localstack.utils import diagnose

        return {
            "version": {
                "image-version": call_safe(diagnose.get_docker_image_details),
                "localstack-version": call_safe(diagnose.get_localstack_version),
                "host": {
                    "kernel": call_safe(diagnose.get_host_kernel_version),
                },
            },
            "info": call_safe(InfoResource.get_info_data),
            "services": call_safe(diagnose.get_service_stats),
            "config": call_safe(diagnose.get_localstack_config),
            "docker-inspect": call_safe(diagnose.inspect_main_container),
            "docker-dependent-image-hashes": call_safe(diagnose.get_important_image_hashes),
            "file-tree": call_safe(diagnose.get_file_tree),
            "important-endpoints": call_safe(diagnose.resolve_endpoints),
            "logs": call_safe(diagnose.get_localstack_logs),
            "usage": call_safe(diagnose.get_usage),
        }


class PluginsResource:
    """
    Resource to list information about plux plugins.
    """

    plugin_managers: list[PluginManager] = []

    def __init__(self):
        # defer imports here to lazy-load code
        from localstack.aws.services.plugins import SERVICE_PLUGINS
        from localstack.platform.runtime import hooks, init

        # service providers
        PluginsResource.plugin_managers.append(SERVICE_PLUGINS.plugin_manager)
        # init script runners
        PluginsResource.plugin_managers.append(init.init_script_manager().runner_manager)
        # init hooks
        PluginsResource.plugin_managers.append(hooks.configure_localstack_container.manager)
        PluginsResource.plugin_managers.append(hooks.prepare_host.manager)
        PluginsResource.plugin_managers.append(hooks.on_infra_ready.manager)
        PluginsResource.plugin_managers.append(hooks.on_infra_start.manager)
        PluginsResource.plugin_managers.append(hooks.on_infra_shutdown.manager)

    def on_get(self, request):
        return {
            manager.namespace: [
                self._get_plugin_details(manager, name) for name in manager.list_names()
            ]
            for manager in self.plugin_managers
        }

    def _get_plugin_details(self, manager: PluginManager, plugin_name: str) -> dict:
        container = manager.get_container(plugin_name)

        details = {
            "name": plugin_name,
            "is_initialized": container.is_init,
            "is_loaded": container.is_loaded,
        }

        # optionally add requires_license information if the plugin provides it
        requires_license = None
        if container.plugin:
            try:
                requires_license = container.plugin.requires_license
            except AttributeError:
                pass
        if requires_license is not None:
            details["requires_license"] = requires_license

        return details


class InitScriptsResource:
    def on_get(self, request):
        from localstack.platform.runtime.init import init_script_manager

        manager = init_script_manager()

        return {
            "completed": {
                stage.name: completed for stage, completed in manager.stage_completed.items()
            },
            "scripts": [
                {
                    "stage": script.stage.name,
                    "name": os.path.basename(script.path),
                    "state": script.state.name,
                }
                for scripts in manager.scripts.values()
                for script in scripts
            ],
        }


class InitScriptsStageResource:
    def on_get(self, request, stage: str):
        from localstack.platform.runtime.init import Stage, init_script_manager

        manager = init_script_manager()

        try:
            stage = Stage[stage.upper()]
        except KeyError:
            return Response(f"no such stage {stage}", 404)

        return {
            "completed": manager.stage_completed.get(stage),
            "scripts": [
                {
                    "stage": script.stage.name,
                    "name": os.path.basename(script.path),
                    "state": script.state.name,
                }
                for script in manager.scripts.get(stage)
            ],
        }


class ConfigResource:
    def on_get(self, request):
        from localstack.utils import diagnose

        return call_safe(diagnose.get_localstack_config)

    def on_post(self, request: Request):
        from localstack.utils.config_listener import update_config_variable

        data = request.get_json(force=True)
        variable = data.get("variable", "")
        if not re.match(r"^[_a-zA-Z0-9]+$", variable):
            return Response("{}", mimetype="application/json", status=400)
        new_value = data.get("value")
        if is_number(new_value):
            new_value = float(new_value)
        update_config_variable(variable, new_value)
        value = getattr(config, variable, None)
        return {
            "variable": variable,
            "value": value,
        }


def _ensure_cloud_registry():
    from localstack.cloud.builtin import register_builtins
    from localstack.cloud.registry import registry as cloud_registry

    if len(cloud_registry) == 0:
        register_builtins(cloud_registry)
    return cloud_registry


class CloudsListResource:
    def on_get(self, request):
        reg = _ensure_cloud_registry()
        clouds = []
        for provider in reg:
            try:
                count = len(provider.list_services())
            except Exception:
                count = 0
            clouds.append(
                {
                    "name": provider.name,
                    "display_name": provider.display_name,
                    "package": provider.package,
                    "services_count": count,
                }
            )
        return {"clouds": clouds}


class CloudHealthResource:
    def __init__(self, service_manager):
        self._aws_health = HealthResource(service_manager)

    def on_get(self, request, cloud: str):
        cloud = (cloud or "").lower()
        if cloud == "aws":
            result = self._aws_health.on_get(request)
            if isinstance(result, dict):
                result.setdefault("cloud", "aws")
            return result

        reg = _ensure_cloud_registry()
        provider = reg.get(cloud)
        if provider is None:
            return Response(
                f'{{"error":"unknown cloud: {cloud}"}}', 404, mimetype="application/json"
            )
        try:
            services = provider.list_services()
        except Exception as e:
            LOG.exception("failed to list services for cloud %s", cloud)
            services = {}
            error = str(e)
        else:
            error = None
        body = {
            "cloud": provider.name,
            "display_name": provider.display_name,
            "edition": get_localstack_edition(),
            "version": constants.VERSION,
            "services": services,
        }
        if error:
            body["error"] = error
        return body


class CloudInfoResource:
    def on_get(self, request, cloud: str):
        cloud = (cloud or "").lower()
        reg = _ensure_cloud_registry()
        provider = reg.get(cloud)
        if provider is None:
            return Response(
                f'{{"error":"unknown cloud: {cloud}"}}', 404, mimetype="application/json"
            )
        base = InfoResource.get_info_data()
        try:
            services_count = len(provider.list_services())
        except Exception:
            services_count = 0
        meta = provider.metadata or {}
        base.update(
            {
                "cloud": provider.name,
                "display_name": provider.display_name,
                "package": provider.package,
                "edge_hosts": list(provider.edge_hosts),
                "services_count": services_count,
                "scope_terms": meta.get("scope_terms", {}),
                "auth": meta.get("auth"),
                "id_format": meta.get("id_format"),
            }
        )
        return base


# ---------------------------------------------------------------------------
# Console passthrough (CLI + IaC) — see docs/multi-cloud-console-plan.md §7
# ---------------------------------------------------------------------------

_CLI_ALLOWLIST = ("aws", "az", "gcloud")
_IAC_TOOL_ALLOWLIST = ("terraform", "serverless")
_IAC_ACTION_ALLOWLIST = ("plan", "apply", "destroy")
_SHELL_METACHARS = re.compile(r"[;&|`$><\n\r]")
_ENV_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_SESSION_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_IAC_MAX_SNIPPET = 64 * 1024
_CLI_TIMEOUT = 30
_IAC_TIMEOUT = 120
_CONSOLE_IAC_ROOT = pathlib.Path(os.path.expanduser("~/.localstack/console-iac"))


def _validate_args(args) -> str | None:
    if not isinstance(args, list):
        return "args must be a list"
    for a in args:
        if not isinstance(a, str):
            return "each arg must be a string"
        if _SHELL_METACHARS.search(a):
            return "shell metachar in arg"
    return None


def _validate_env(env) -> str | None:
    if env is None:
        return None
    if not isinstance(env, dict):
        return "env must be an object"
    for k, v in env.items():
        if not isinstance(k, str) or not _ENV_KEY_RE.match(k):
            return f"invalid env key: {k!r}"
        if not isinstance(v, str) or _SHELL_METACHARS.search(v):
            return f"invalid env value for {k}"
    return None


def _cli_default_env(cli: str) -> dict:
    if cli == "aws":
        return {
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_ENDPOINT_URL": "http://localhost:4566",
        }
    if cli == "az":
        return {"AZURE_HTTP_USER_AGENT": "localstack-console"}
    if cli == "gcloud":
        return {"CLOUDSDK_CORE_PROJECT": "localstack-project"}
    return {}


def _terraform_provider_block() -> str:
    """Generate a provider.tf wrapper pointing all providers at LocalStack."""
    return '''terraform {
  required_providers {
    aws     = { source = "hashicorp/aws",     version = "~> 5.0" }
    azurerm = { source = "hashicorp/azurerm", version = "~> 3.0" }
    google  = { source = "hashicorp/google",  version = "~> 5.0" }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true
  endpoints {
    s3             = "http://localhost:4566"
    sqs            = "http://localhost:4566"
    dynamodb       = "http://localhost:4566"
    lambda         = "http://localhost:4566"
    iam            = "http://localhost:4566"
    sts            = "http://localhost:4566"
    secretsmanager = "http://localhost:4566"
    kms            = "http://localhost:4566"
    apigateway     = "http://localhost:4566"
    sns            = "http://localhost:4566"
    cloudwatch     = "http://localhost:4566"
    events         = "http://localhost:4566"
    logs           = "http://localhost:4566"
  }
}

provider "azurerm" {
  features {}
  skip_provider_registration = true
  client_id                  = "00000000-0000-0000-0000-000000000000"
  client_secret              = "test"
  tenant_id                  = "00000000-0000-0000-0000-000000000000"
  subscription_id            = "00000000-0000-0000-0000-000000000000"
  environment                = "public"
}

provider "google" {
  project = "localstack-project"
  region  = "us-central1"
}
'''


class CliPassthroughResource:
    """POST /_localstack/console/cli — execute aws|az|gcloud inside the
    LocalStack process.

    NOTE: assumes the host has the CLI on PATH. The recommended deployment
    runs the separate host-side bridge (`bin/console-cli-bridge`) so the
    LocalStack container does not need to ship multi-GB CLIs. This endpoint
    is the in-container fallback for the SPA.
    """

    def on_post(self, request: Request):
        try:
            data = request.get_json(True, True) or {}
        except Exception:
            return Response('{"error":"invalid json"}', 400, mimetype="application/json")

        cli = data.get("cli")
        if cli not in _CLI_ALLOWLIST:
            return Response(
                json.dumps({"error": "cli not in allowlist", "cli": cli}),
                400,
                mimetype="application/json",
            )

        args = data.get("args", [])
        err = _validate_args(args)
        if err:
            return Response(
                json.dumps({"error": err}), 400, mimetype="application/json"
            )

        env_overrides = data.get("env")
        err = _validate_env(env_overrides)
        if err:
            return Response(
                json.dumps({"error": err}), 400, mimetype="application/json"
            )

        binary = shutil.which(cli)
        if not binary:
            return Response(
                json.dumps({"error": "cli not available on host", "cli": cli}),
                503,
                mimetype="application/json",
            )

        env = dict(os.environ)
        env.update(_cli_default_env(cli))
        if env_overrides:
            env.update(env_overrides)

        session_id = uuid.uuid4().hex
        started = time.monotonic()
        try:
            proc = subprocess.run(
                [binary, *args],
                env=env,
                capture_output=True,
                text=True,
                timeout=_CLI_TIMEOUT,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            return Response(
                json.dumps(
                    {
                        "error": "timeout",
                        "session_id": session_id,
                        "cli": cli,
                        "args": args,
                        "duration_ms": duration_ms,
                        "stdout": exc.stdout or "",
                        "stderr": exc.stderr or "",
                    }
                ),
                504,
                mimetype="application/json",
            )
        except OSError as exc:
            LOG.exception("cli passthrough failed: %s", cli)
            return Response(
                json.dumps({"error": "exec failed", "detail": str(exc)}),
                500,
                mimetype="application/json",
            )

        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "session_id": session_id,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_ms": duration_ms,
        }


def _iac_validate(data):
    tool = data.get("tool")
    if tool not in _IAC_TOOL_ALLOWLIST:
        return None, ("tool not in allowlist", 400)
    snippet = data.get("snippet", "")
    if not isinstance(snippet, str):
        return None, ("snippet must be a string", 400)
    if len(snippet.encode("utf-8")) > _IAC_MAX_SNIPPET:
        return None, ("snippet exceeds 64KB limit", 400)
    return (tool, snippet), None


def _iac_render_files(tool: str, snippet: str) -> dict:
    if tool == "terraform":
        return {"provider.tf": _terraform_provider_block(), "main.tf": snippet}
    # serverless
    return {"serverless.yml": snippet}


class IacApplyResource:
    """POST /_localstack/console/iac — write snippet to temp dir and run
    terraform/serverless. Synchronous. TODO: SSE streaming (plan §3.4).
    """

    def on_post(self, request: Request):
        try:
            data = request.get_json(True, True) or {}
        except Exception:
            return Response('{"error":"invalid json"}', 400, mimetype="application/json")

        validated, err = _iac_validate(data)
        if err:
            return Response(
                json.dumps({"error": err[0]}), err[1], mimetype="application/json"
            )
        tool, snippet = validated

        action = data.get("action")
        if action not in _IAC_ACTION_ALLOWLIST:
            return Response(
                json.dumps({"error": "action not in allowlist"}),
                400,
                mimetype="application/json",
            )

        binary = shutil.which(tool)
        if not binary:
            return Response(
                json.dumps({"error": "tool not installed on host", "tool": tool}),
                503,
                mimetype="application/json",
            )

        session_id = uuid.uuid4().hex
        session_dir = _CONSOLE_IAC_ROOT / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        for name, content in _iac_render_files(tool, snippet).items():
            (session_dir / name).write_text(content)

        log_path = session_dir / "exec.log"
        env = dict(os.environ)
        env.update(_cli_default_env("aws"))

        started = time.monotonic()
        combined_stdout = []
        combined_stderr = []

        def _run(cmd: list[str]) -> int:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(session_dir),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=_IAC_TIMEOUT,
                )
            except subprocess.TimeoutExpired as exc:
                combined_stdout.append(exc.stdout or "")
                combined_stderr.append(exc.stderr or "")
                combined_stderr.append("\n[localstack] timeout\n")
                return 124
            combined_stdout.append(proc.stdout or "")
            combined_stderr.append(proc.stderr or "")
            return proc.returncode

        if tool == "terraform":
            rc = _run([binary, "init", "-input=false", "-no-color"])
            if rc == 0:
                cmd = [binary, action, "-input=false", "-no-color"]
                if action in ("apply", "destroy"):
                    cmd.append("-auto-approve")
                rc = _run(cmd)
        else:
            cmd = [binary, action, "--stage", "local"]
            rc = _run(cmd)

        duration_ms = int((time.monotonic() - started) * 1000)
        stdout = "".join(combined_stdout)
        stderr = "".join(combined_stderr)
        log_path.write_text(
            f"# session {session_id}\n# tool {tool} action {action}\n# duration_ms {duration_ms}\n"
            f"# exit_code {rc}\n\n=== STDOUT ===\n{stdout}\n=== STDERR ===\n{stderr}\n"
        )

        return {
            "session_id": session_id,
            "exit_code": rc,
            "stdout": stdout,
            "stderr": stderr,
            "log_path": str(log_path),
            "duration_ms": duration_ms,
        }


class IacPreviewResource:
    """POST /_localstack/console/iac/preview — render the files that would
    be written by IacApply. Pure render, no execution.
    """

    def on_post(self, request: Request):
        try:
            data = request.get_json(True, True) or {}
        except Exception:
            return Response('{"error":"invalid json"}', 400, mimetype="application/json")

        validated, err = _iac_validate(data)
        if err:
            return Response(
                json.dumps({"error": err[0]}), err[1], mimetype="application/json"
            )
        tool, snippet = validated
        return {"tool": tool, "files": _iac_render_files(tool, snippet)}


class SessionLogResource:
    """GET /_localstack/console/sessions/<session_id>/log — return exec.log."""

    def on_get(self, request: Request, session_id: str):
        if not _SESSION_ID_RE.match(session_id or ""):
            return Response('{"error":"invalid session_id"}', 404, mimetype="application/json")
        log_path = _CONSOLE_IAC_ROOT / session_id / "exec.log"
        if not log_path.is_file():
            return Response('{"error":"log not found"}', 404, mimetype="application/json")
        return Response(log_path.read_text(), 200, mimetype="text/plain")


class LocalstackResources(Router):
    """
    Router for localstack-internal HTTP resources.
    """

    def __init__(self):
        super().__init__(dispatcher=handler_dispatcher())
        self.add_default_routes()
        # TODO: load routes as plugins

    def add_default_routes(self):
        from localstack.aws.services.plugins import SERVICE_PLUGINS

        health_resource = HealthResource(SERVICE_PLUGINS)
        self.add(Resource("/_localstack/health", health_resource))
        self.add(Resource("/_localstack/info", InfoResource()))
        self.add(Resource("/_localstack/plugins", PluginsResource()))
        self.add(Resource("/_localstack/init", InitScriptsResource()))
        self.add(Resource("/_localstack/init/<stage>", InitScriptsStageResource()))
        self.add(Resource("/_localstack/clouds", CloudsListResource()))
        self.add(Resource("/_localstack/clouds/<cloud>/health", CloudHealthResource(SERVICE_PLUGINS)))
        self.add(Resource("/_localstack/clouds/<cloud>/info", CloudInfoResource()))
        self.add(Resource("/_localstack/console/cli", CliPassthroughResource()))
        self.add(Resource("/_localstack/console/iac", IacApplyResource()))
        self.add(Resource("/_localstack/console/iac/preview", IacPreviewResource()))
        self.add(
            Resource(
                "/_localstack/console/sessions/<session_id>/log",
                SessionLogResource(),
            )
        )

        if config.ENABLE_CONFIG_UPDATES:
            LOG.warning(
                "Enabling config endpoint, "
                "please be aware that this can expose sensitive information via your network."
            )
            self.add(Resource("/_localstack/config", ConfigResource()))

        if config.DEBUG:
            LOG.warning(
                "Enabling diagnose endpoint, "
                "please be aware that this can expose sensitive information via your network."
            )
            self.add(Resource("/_localstack/diagnose", DiagnoseResource()))
            self.add(Resource("/_localstack/usage", UsageResource()))


@singleton_factory
def get_internal_apis() -> LocalstackResources:
    """
    Get the LocalstackResources singleton.
    """
    return LocalstackResources()
