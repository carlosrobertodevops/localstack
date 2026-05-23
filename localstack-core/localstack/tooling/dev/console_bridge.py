"""Host-side CLI bridge worker for the multi-cloud console.

Listens on 127.0.0.1:4578 by default and exposes `/exec` + `/exec/stream`
endpoints so the SPA at :4577 (or Vite dev :5173) can invoke the locally-
installed `aws`/`az`/`gcloud` CLIs without shipping them inside the
LocalStack container.

See docs/multi-cloud-console-plan.md §3.5, §4.

Run via:
    python -m localstack.tooling.dev.console_bridge
or via the shell wrapper:
    ./bin/console-cli-bridge

This module hosts the validators (importable for tests). The aiohttp app
is built lazily so the validators do not require aiohttp to be installed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

LOG = logging.getLogger("console_bridge")

CLI_ALLOWLIST = ("aws", "az", "gcloud")
SHELL_METACHARS = re.compile(r"[;&|`$><\n\r]")
ENV_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4578
EXEC_TIMEOUT = 30

DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:4577",
    "http://127.0.0.1:4577",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def validate_cli(cli: str) -> None:
    if cli not in CLI_ALLOWLIST:
        raise ValueError(f"cli not in allowlist: {cli!r}")


def validate_args(args) -> None:
    if not isinstance(args, list):
        raise ValueError("args must be a list")
    for a in args:
        if not isinstance(a, str):
            raise ValueError("each arg must be a string")
        if SHELL_METACHARS.search(a):
            raise ValueError(f"shell metachar in arg: {a!r}")


def validate_env(env) -> None:
    if env is None:
        return
    if not isinstance(env, dict):
        raise ValueError("env must be an object")
    for k, v in env.items():
        if not isinstance(k, str) or not ENV_KEY_RE.match(k):
            raise ValueError(f"invalid env key: {k!r}")
        if not isinstance(v, str) or SHELL_METACHARS.search(v):
            raise ValueError(f"invalid env value for {k}")


def resolve_binary(cli: str) -> str | None:
    """Prefer the sibling wrappers (bin/awslocal-dev etc.) over raw aws/az/gcloud.

    The wrappers set AWS/Azure/GCP env vars to point at LocalStack.
    """
    wrapper_map = {
        "aws": "awslocal-dev",
        "az": "azurelocal",
        "gcloud": "gcloudlocal",
    }
    # Walk up from this file to repo root; wrappers live at <repo>/bin/.
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "bin" / wrapper_map[cli]
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which(cli)


def build_env(cli: str, overrides: dict | None) -> dict:
    env = dict(os.environ)
    if cli == "aws":
        env.setdefault("AWS_ACCESS_KEY_ID", "test")
        env.setdefault("AWS_SECRET_ACCESS_KEY", "test")
        env.setdefault("AWS_DEFAULT_REGION", "us-east-1")
        env.setdefault("AWS_ENDPOINT_URL", "http://localhost:4566")
    if overrides:
        env.update(overrides)
    return env


def cli_status() -> dict:
    return {
        cli: bool(resolve_binary(cli) or shutil.which(cli)) for cli in CLI_ALLOWLIST
    } | {"terraform": bool(shutil.which("terraform"))}


# ---------------------------------------------------------------------------
# aiohttp app (only built when actually serving — keeps the module lightweight
# for tests that just exercise the validators).
# ---------------------------------------------------------------------------


def _build_app(allowed_origins: tuple[str, ...]):
    from aiohttp import web

    routes = web.RouteTableDef()

    def _cors_headers(request) -> dict:
        origin = request.headers.get("Origin", "")
        headers = {"Vary": "Origin"}
        if origin in allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "Content-Type"
        return headers

    @routes.options("/{tail:.*}")
    async def preflight(request):
        return web.Response(status=204, headers=_cors_headers(request))

    @routes.get("/health")
    async def health(request):
        return web.json_response(
            {"status": "ok", "version": "0.1.0", "cli": cli_status()},
            headers=_cors_headers(request),
        )

    @routes.post("/exec")
    async def exec_cmd(request):
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "invalid json"}, status=400, headers=_cors_headers(request)
            )

        cli = data.get("cli")
        args = data.get("args", [])
        env_overrides = data.get("env")

        try:
            validate_cli(cli)
            validate_args(args)
            validate_env(env_overrides)
        except ValueError as exc:
            return web.json_response(
                {"error": str(exc)}, status=400, headers=_cors_headers(request)
            )

        binary = resolve_binary(cli)
        if not binary:
            return web.json_response(
                {"error": "cli not available on host", "cli": cli},
                status=503,
                headers=_cors_headers(request),
            )

        env = build_env(cli, env_overrides)
        session_id = uuid.uuid4().hex
        started = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                binary,
                *args,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=EXEC_TIMEOUT
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            duration_ms = int((time.monotonic() - started) * 1000)
            LOG.info(
                "exec timeout cli=%s args=%d duration_ms=%d", cli, len(args), duration_ms
            )
            return web.json_response(
                {
                    "error": "timeout",
                    "session_id": session_id,
                    "duration_ms": duration_ms,
                },
                status=504,
                headers=_cors_headers(request),
            )

        duration_ms = int((time.monotonic() - started) * 1000)
        LOG.info(
            "exec cli=%s args=%d exit=%d duration_ms=%d",
            cli,
            len(args),
            proc.returncode,
            duration_ms,
        )
        return web.json_response(
            {
                "session_id": session_id,
                "exit_code": proc.returncode,
                "stdout": stdout_b.decode("utf-8", errors="replace"),
                "stderr": stderr_b.decode("utf-8", errors="replace"),
                "duration_ms": duration_ms,
            },
            headers=_cors_headers(request),
        )

    @routes.post("/exec/stream")
    async def exec_stream(request):
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "invalid json"}, status=400, headers=_cors_headers(request)
            )

        cli = data.get("cli")
        args = data.get("args", [])
        env_overrides = data.get("env")

        try:
            validate_cli(cli)
            validate_args(args)
            validate_env(env_overrides)
        except ValueError as exc:
            return web.json_response(
                {"error": str(exc)}, status=400, headers=_cors_headers(request)
            )

        binary = resolve_binary(cli)
        if not binary:
            return web.json_response(
                {"error": "cli not available on host", "cli": cli},
                status=503,
                headers=_cors_headers(request),
            )

        env = build_env(cli, env_overrides)
        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                **_cors_headers(request),
            },
        )
        await response.prepare(request)

        proc = await asyncio.create_subprocess_exec(
            binary,
            *args,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def pipe(stream, event_name):
            while True:
                line = await stream.readline()
                if not line:
                    break
                payload = json.dumps({"line": line.decode("utf-8", errors="replace")})
                await response.write(
                    f"event: {event_name}\ndata: {payload}\n\n".encode("utf-8")
                )

        try:
            await asyncio.gather(
                pipe(proc.stdout, "stdout"), pipe(proc.stderr, "stderr")
            )
            await proc.wait()
        except asyncio.CancelledError:
            proc.kill()
            raise

        await response.write(
            f"event: exit\ndata: {json.dumps({'code': proc.returncode})}\n\n".encode(
                "utf-8"
            )
        )
        return response

    app = web.Application()
    app.add_routes(routes)
    return app


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="LocalStack console CLI bridge")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument(
        "--allow-origin",
        action="append",
        default=[],
        help="Additional CORS allowed origin (repeatable)",
    )
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        LOG.warning(
            "binding to non-loopback host %s — this exposes shell exec to the network",
            args.host,
        )
    allowed = tuple(DEFAULT_ALLOWED_ORIGINS) + tuple(args.allow_origin)
    try:
        from aiohttp import web
    except ImportError:
        LOG.error(
            "aiohttp not installed. Install: pip install -r bin/console-cli-bridge.requirements.txt"
        )
        return 1
    app = _build_app(allowed)
    LOG.info("console bridge listening on %s:%d", args.host, args.port)
    web.run_app(app, host=args.host, port=args.port, print=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
