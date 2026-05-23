"""WSGI router for the Azure Cosmos DB SQL API item subset."""

from __future__ import annotations

import json
from typing import Any

from werkzeug.wrappers import Request, Response

from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.services.cosmos.provider import MicrosoftDocumentDBProvider


def _json(payload: dict[str, Any] | list, status: int = 200) -> Response:
    return Response(json.dumps(payload), status=status, mimetype="application/json")


def _error(code: str, message: str, status: int) -> Response:
    return _json({"code": code, "message": message}, status=status)


class CosmosSqlRouter:
    """Path layout: /{account}/dbs/{db}/colls/{coll}/docs[/{id}]."""

    def __init__(self, provider: MicrosoftDocumentDBProvider) -> None:
        self.provider = provider

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self._dispatch(request)
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        parts = request.path.strip("/").split("/")
        if len(parts) not in (6, 7) or parts[1] != "dbs" or parts[3] != "colls" or parts[5] != "docs":
            return _error("NotFound", "expected /{account}/dbs/{db}/colls/{coll}/docs[/{id}]", 404)
        account, _, db, _, coll, _, *rest = parts
        item_id = rest[0] if rest else None

        try:
            if item_id is None:
                return self._collection_op(request, account, db, coll)
            return self._item_op(request, account, db, coll, item_id)
        except AzureNotFound as exc:
            return _error("NotFound", str(exc), 404)
        except AzureInvalidRequest as exc:
            return _error("BadRequest", str(exc), 400)

    def _collection_op(
        self, request: Request, account: str, db: str, coll: str
    ) -> Response:
        if request.method == "POST":
            try:
                body = json.loads(request.get_data(as_text=True) or "{}")
            except json.JSONDecodeError:
                return _error("BadRequest", "body is not valid JSON", 400)
            saved = self.provider.upsert_item(account, db, coll, body)
            return _json(saved, status=201)
        if request.method == "GET":
            docs = self.provider.list_items(account, db, coll)
            return _json({"Documents": docs, "_count": len(docs)})
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    def _item_op(
        self, request: Request, account: str, db: str, coll: str, item_id: str
    ) -> Response:
        if request.method == "GET":
            return _json(self.provider.get_item(account, db, coll, item_id))
        if request.method == "PUT":
            try:
                body = json.loads(request.get_data(as_text=True) or "{}")
            except json.JSONDecodeError:
                return _error("BadRequest", "body is not valid JSON", 400)
            if body.get("id") != item_id:
                return _error("BadRequest", "path id must match body id", 400)
            saved = self.provider.upsert_item(account, db, coll, body)
            return _json(saved)
        if request.method == "DELETE":
            self.provider.delete_item(account, db, coll, item_id)
            return Response(status=204)
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)
