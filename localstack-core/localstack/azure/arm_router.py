"""WSGI router exposing the Azure Resource Manager subset over HTTP."""

from __future__ import annotations

import json
from typing import Any, Callable

from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response

from localstack.azure.arm_serializers import (
    deserialize_resource_body,
    deserialize_resource_group_body,
    serialize_resource,
    serialize_resource_group,
    serialize_resource_group_list,
    serialize_resource_list,
)
from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.resource_manager import ResourceManagerProvider
from localstack.azure.scope import AzureScope


def _json_response(payload: dict[str, Any], status: int = 200) -> Response:
    return Response(json.dumps(payload), status=status, mimetype="application/json")


def _error(code: str, message: str, status: int) -> Response:
    return _json_response({"error": {"code": code, "message": message}}, status=status)


class ArmRouter:
    """Minimal ARM REST surface for resource groups + generic resources."""

    def __init__(self, provider: ResourceManagerProvider) -> None:
        self.provider = provider
        self.url_map = Map(
            [
                Rule(
                    "/subscriptions/<sub>/resourceGroups",
                    endpoint="resource_groups",
                    methods=["GET"],
                ),
                Rule(
                    "/subscriptions/<sub>/resourceGroups/<rg>",
                    endpoint="resource_group",
                    methods=["PUT", "GET", "DELETE"],
                ),
                Rule(
                    "/subscriptions/<sub>/resourceGroups/<rg>/providers/<ns>/<rtype>",
                    endpoint="resources_by_type",
                    methods=["GET"],
                ),
                Rule(
                    "/subscriptions/<sub>/resourceGroups/<rg>/providers/<ns>/<rtype>/<name>",
                    endpoint="resource",
                    methods=["PUT", "GET", "DELETE"],
                ),
            ]
        )

    # WSGI entrypoint
    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        adapter = self.url_map.bind_to_environ(environ)
        try:
            endpoint, values = adapter.match()
        except HTTPException as exc:
            return exc(environ, start_response)
        handler: Callable[..., Response] = getattr(self, f"_handle_{endpoint}")
        try:
            response = handler(request, **values)
        except AzureNotFound as exc:
            response = _error(self._notfound_code(exc), str(exc), 404)
        except AzureInvalidRequest as exc:
            response = _error("BadRequest", str(exc), 400)
        except json.JSONDecodeError as exc:
            response = _error("InvalidJson", f"request body is not valid JSON: {exc.msg}", 400)
        except NotFound:
            response = _error("NotFound", "route not found", 404)
        return response(environ, start_response)

    # -- handlers --

    def _handle_resource_groups(self, request: Request, *, sub: str) -> Response:
        scope = AzureScope.for_subscription(sub)
        return _json_response(serialize_resource_group_list(self.provider.list_resource_groups(scope)))

    def _handle_resource_group(self, request: Request, *, sub: str, rg: str) -> Response:
        scope = AzureScope.for_subscription(sub)
        if request.method == "PUT":
            body = self._json_body(request)
            params = deserialize_resource_group_body(body)
            group = self.provider.create_or_update_resource_group(scope, rg, params)
            return _json_response(serialize_resource_group(group))
        if request.method == "GET":
            return _json_response(serialize_resource_group(self.provider.get_resource_group(scope, rg)))
        if request.method == "DELETE":
            self.provider.delete_resource_group(scope, rg)
            return Response(status=204)
        raise NotFound()

    def _handle_resources_by_type(
        self, request: Request, *, sub: str, rg: str, ns: str, rtype: str
    ) -> Response:
        scope = AzureScope.for_subscription(sub)
        type_filter = f"{ns}/{rtype}".lower()
        all_resources = self.provider.list_resources(scope, resource_group=rg)
        filtered = [r for r in all_resources if r.type.lower() == type_filter]
        return _json_response(serialize_resource_list(filtered))

    def _handle_resource(
        self, request: Request, *, sub: str, rg: str, ns: str, rtype: str, name: str
    ) -> Response:
        scope = AzureScope.for_subscription(sub)
        resource_id = (
            f"/subscriptions/{sub}/resourceGroups/{rg}/providers/{ns}/{rtype}/{name}"
        )
        if request.method == "PUT":
            body = self._json_body(request)
            params = deserialize_resource_body(body)
            res = self.provider.create_or_update_resource(scope, resource_id, params)
            return _json_response(serialize_resource(res))
        if request.method == "GET":
            return _json_response(serialize_resource(self.provider.get_resource(scope, resource_id)))
        if request.method == "DELETE":
            self.provider.delete_resource(scope, resource_id)
            return Response(status=204)
        raise NotFound()

    # -- helpers --

    @staticmethod
    def _json_body(request: Request) -> dict[str, Any]:
        raw = request.get_data(as_text=True) or "{}"
        return json.loads(raw)

    @staticmethod
    def _notfound_code(exc: AzureNotFound) -> str:
        msg = str(exc).lower()
        if "resource group" in msg:
            return "ResourceGroupNotFound"
        return "ResourceNotFound"
