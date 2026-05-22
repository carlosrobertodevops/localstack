"""IAM/OAuth2 token endpoint router.

| Method | Path                              | Action            |
| ------ | --------------------------------- | ----------------- |
| POST   | /token                            | mint access token |
| POST   | /oauth2/v4/token                  | mint access token |
| POST   | /v1/projects/{p}/serviceAccounts  | create SA         |
| GET    | /v1/projects/{p}/serviceAccounts  | list SAs          |
| GET    | /v1/projects/{p}/serviceAccounts/{email} | get SA     |
| DELETE | /v1/projects/{p}/serviceAccounts/{email} | delete SA  |
"""

from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.iam.provider import IamProvider


_TOKEN_PATHS = frozenset({"/token", "/oauth2/v4/token", "/oauth2/v3/token"})


class IamTokenRouter:
    def __init__(self, *, provider: IamProvider) -> None:
        self.provider = provider

    def __call__(self, environ, start_response):
        request = Request(environ)
        try:
            response = self._dispatch(request)
        except GcpError as exc:
            status, body = serialize_error(exc)
            response = Response(body, status=status, mimetype="application/json")
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        path = request.path
        method = request.method.upper()

        if path in _TOKEN_PATHS:
            if method != "POST":
                raise GcpInvalidRequest(f"method {method} not allowed on {path}")
            return self._handle_token(request)

        if path.startswith("/v1/projects/"):
            return self._handle_service_accounts(request, method)

        raise GcpNotFound(f"unknown path: {path}")

    def _handle_token(self, request: Request) -> Response:
        # form-encoded body (OAuth2)
        form = request.form
        grant_type = form.get("grant_type", "client_credentials")
        payload = dict(form)
        self.provider.validate_grant(grant_type, payload)
        token = self.provider.mint_access_token(
            audience=payload.get("audience", "https://www.googleapis.com/"),
            scope=payload.get("scope", ""),
            email=payload.get("client_id"),
        )
        return Response(json.dumps(token), status=200, mimetype="application/json")

    def _handle_service_accounts(self, request: Request, method: str) -> Response:
        rest = request.path[len("/v1/projects/") :]
        parts = rest.split("/")
        if len(parts) < 2 or parts[1] != "serviceAccounts":
            raise GcpNotFound(f"unknown path: {request.path}")
        project = parts[0]
        tail = parts[2] if len(parts) > 2 else ""

        if not tail:
            if method == "POST":
                body = parse_json_body(request.get_data())
                account_id = body.get("accountId")
                if not account_id:
                    raise GcpInvalidRequest("'accountId' required")
                sa_body = body.get("serviceAccount") or {}
                sa = self.provider.create_service_account(
                    project,
                    account_id,
                    display_name=sa_body.get("displayName", ""),
                )
                return self._json(sa.to_dict())
            if method == "GET":
                accs = self.provider.list_service_accounts(project)
                return self._json({"accounts": [a.to_dict() for a in accs]})
            raise GcpInvalidRequest(f"method {method} not allowed")

        full = f"projects/{project}/serviceAccounts/{tail}"
        if method == "GET":
            return self._json(self.provider.get_service_account(full).to_dict())
        if method == "DELETE":
            self.provider.delete_service_account(full)
            return self._json({})
        raise GcpInvalidRequest(f"method {method} not allowed on service account")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
