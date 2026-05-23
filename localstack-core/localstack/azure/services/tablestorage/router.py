"""Azure Table Storage REST adapter (subset of REST API 2019-02-02 — OData JSON)."""

from __future__ import annotations

import json
import re

from werkzeug.wrappers import Request, Response

from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.services.tablestorage.provider import TableStorageProvider

_TABLES_RE = re.compile(r"^/(?P<acct>[^/]+)/Tables$")
_TABLE_RE = re.compile(r"^/(?P<acct>[^/]+)/Tables\('(?P<t>[^']+)'\)$")
_ENTITIES_RE = re.compile(r"^/(?P<acct>[^/]+)/(?P<t>[^/]+)\(\)$")
_ENTITY_RE = re.compile(
    r"^/(?P<acct>[^/]+)/(?P<t>[^/]+)\(PartitionKey='(?P<pk>[^']+)',RowKey='(?P<rk>[^']+)'\)$"
)


def _json(payload, status: int = 200) -> Response:
    return Response(
        json.dumps(payload),
        status=status,
        mimetype="application/json;odata=minimalmetadata",
    )


def _error(code: str, msg: str, status: int) -> Response:
    return _json({"odata.error": {"code": code, "message": {"value": msg}}}, status=status)


class TableStorageRouter:
    """Path layout (OData-ish):
    POST /{account}/Tables                                     create table
    DELETE /{account}/Tables('{t}')                            delete table
    GET /{account}/Tables                                       list tables
    POST /{account}/{table}()                                  upsert entity
    GET /{account}/{table}(PartitionKey='..',RowKey='..')      get entity
    DELETE /{account}/{table}(PartitionKey='..',RowKey='..')   delete entity
    GET /{account}/{table}()                                    query entities
    """

    def __init__(self, provider: TableStorageProvider) -> None:
        self.provider = provider

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self._dispatch(request)
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        path = request.path
        try:
            if m := _ENTITY_RE.match(path):
                return self._entity(request, m["acct"], m["t"], m["pk"], m["rk"])
            if m := _ENTITIES_RE.match(path):
                return self._entities(request, m["acct"], m["t"])
            if m := _TABLE_RE.match(path):
                return self._table(request, m["acct"], m["t"])
            if m := _TABLES_RE.match(path):
                return self._tables(request, m["acct"])
        except AzureNotFound as exc:
            return _error("ResourceNotFound", str(exc), 404)
        except AzureInvalidRequest as exc:
            return _error("InvalidInput", str(exc), 400)
        return _error("ResourceNotFound", "unsupported table storage path", 404)

    # -- tables --

    def _tables(self, request: Request, acct: str) -> Response:
        if request.method == "POST":
            body = self._json_body(request)
            name = body.get("TableName")
            if not name:
                return _error("InvalidInput", "TableName required", 400)
            self.provider.create_table(acct, name)
            return _json({"TableName": name}, status=201)
        if request.method == "GET":
            tables = self.provider.list_tables(acct)
            return _json({"value": [{"TableName": t.name} for t in tables]})
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    def _table(self, request: Request, acct: str, name: str) -> Response:
        if request.method == "DELETE":
            self.provider.delete_table(acct, name)
            return Response(status=204)
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    # -- entities --

    def _entities(self, request: Request, acct: str, table: str) -> Response:
        if request.method == "POST":
            entity = self._json_body(request)
            saved = self.provider.upsert_entity(acct, table, entity)
            return _json(saved, status=201)
        if request.method == "GET":
            pk = request.args.get("$filter")
            partition_key = None
            if pk and "PartitionKey eq" in pk:
                # quick parse: PartitionKey eq 'X'
                m = re.search(r"PartitionKey eq '([^']+)'", pk)
                if m:
                    partition_key = m.group(1)
            entities = self.provider.query_entities(acct, table, partition_key=partition_key)
            return _json({"value": entities})
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    def _entity(
        self, request: Request, acct: str, table: str, pk: str, rk: str
    ) -> Response:
        if request.method == "GET":
            return _json(self.provider.get_entity(acct, table, pk, rk))
        if request.method == "PUT":
            entity = self._json_body(request)
            entity["PartitionKey"] = pk
            entity["RowKey"] = rk
            saved = self.provider.upsert_entity(acct, table, entity)
            return _json(saved)
        if request.method == "DELETE":
            self.provider.delete_entity(acct, table, pk, rk)
            return Response(status=204)
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    @staticmethod
    def _json_body(request: Request) -> dict:
        raw = request.get_data(as_text=True) or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AzureInvalidRequest(f"invalid JSON: {exc.msg}")
