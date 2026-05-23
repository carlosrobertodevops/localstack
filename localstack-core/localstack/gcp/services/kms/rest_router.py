from __future__ import annotations

import base64
import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.kms.provider import KmsProvider


class KmsRouter:
    def __init__(self, *, provider: KmsProvider) -> None:
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
        if not path.startswith("/v1/projects/"):
            raise GcpNotFound(f"unknown path: {path}")
        rest = path[len("/v1/projects/") :]
        parts = rest.split("/")
        if len(parts) < 4 or parts[1] != "locations" or parts[3] != "keyRings":
            raise GcpNotFound(f"unknown path: {path}")
        project, location = parts[0], parts[2]

        if len(parts) == 4:
            if method == "POST":
                keyring_id = request.args.get("keyRingId")
                if not keyring_id:
                    raise GcpInvalidRequest("keyRingId query parameter required")
                kr = self.provider.create_keyring(project, location, keyring_id)
                return self._json(kr.to_dict())
            if method == "GET":
                krs = self.provider.list_keyrings(project, location)
                return self._json({"keyRings": [kr.to_dict() for kr in krs]})
            raise GcpInvalidRequest(f"method {method} not allowed on /keyRings")

        keyring_id = parts[4]

        if len(parts) == 5:
            if method == "GET":
                return self._json(
                    self.provider.get_keyring(project, location, keyring_id).to_dict()
                )
            raise GcpInvalidRequest(f"method {method} not allowed on keyring")

        if parts[5] != "cryptoKeys":
            raise GcpNotFound(f"unknown segment: {parts[5]}")

        if len(parts) == 6:
            if method == "POST":
                cryptokey_id = request.args.get("cryptoKeyId")
                if not cryptokey_id:
                    raise GcpInvalidRequest("cryptoKeyId query parameter required")
                body = parse_json_body(request.get_data()) if request.get_data() else {}
                ck = self.provider.create_cryptokey(
                    project,
                    location,
                    keyring_id,
                    cryptokey_id,
                    purpose=body.get("purpose", "ENCRYPT_DECRYPT"),
                )
                return self._json(ck.to_dict())
            if method == "GET":
                cks = self.provider.list_cryptokeys(project, location, keyring_id)
                return self._json({"cryptoKeys": [ck.to_dict() for ck in cks]})
            raise GcpInvalidRequest(f"method {method} not allowed on /cryptoKeys")

        ck_segment = parts[6]
        if ":" in ck_segment:
            cryptokey_id, action = ck_segment.split(":", 1)
            return self._cryptokey_action(request, method, project, location, keyring_id, cryptokey_id, action)

        cryptokey_id = ck_segment
        if len(parts) == 7:
            if method == "GET":
                return self._json(
                    self.provider.get_cryptokey(
                        project, location, keyring_id, cryptokey_id
                    ).to_dict()
                )
            raise GcpInvalidRequest(f"method {method} not allowed on cryptokey")

        if parts[7] != "cryptoKeyVersions":
            raise GcpNotFound(f"unknown segment: {parts[7]}")

        if len(parts) == 8 and method == "POST":
            v = self.provider.create_cryptokey_version(
                project, location, keyring_id, cryptokey_id
            )
            return self._json(v.to_dict())

        raise GcpNotFound(f"unknown path: {path}")

    def _cryptokey_action(
        self,
        request: Request,
        method: str,
        project: str,
        location: str,
        keyring_id: str,
        cryptokey_id: str,
        action: str,
    ) -> Response:
        if method != "POST":
            raise GcpInvalidRequest(f"method {method} not allowed for action {action}")
        ck = self.provider.get_cryptokey(project, location, keyring_id, cryptokey_id)
        body = parse_json_body(request.get_data()) if request.get_data() else {}
        if action == "encrypt":
            plaintext = base64.b64decode(body.get("plaintext", ""))
            ciphertext = self.provider.encrypt(ck.name, plaintext)
            return self._json(
                {"name": ck.name, "ciphertext": base64.b64encode(ciphertext).decode("ascii")}
            )
        if action == "decrypt":
            ciphertext = base64.b64decode(body.get("ciphertext", ""))
            plaintext = self.provider.decrypt(ck.name, ciphertext)
            return self._json({"plaintext": base64.b64encode(plaintext).decode("ascii")})
        raise GcpInvalidRequest(f"unknown action: {action}")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
