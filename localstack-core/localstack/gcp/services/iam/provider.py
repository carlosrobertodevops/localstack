from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import json
import secrets
from typing import Any

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.iam.models import IamDataStore, ServiceAccount
from localstack.gcp.stores import GcpStores

_DEFAULT_SECRET = b"localstack-gcp-mock-secret"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class IamProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
        secret: bytes | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = IamDataStore()
        self.secret = secret or _DEFAULT_SECRET

    # --- service accounts ---
    def create_service_account(self, project: str, account_id: str, *, display_name: str = "") -> ServiceAccount:
        email = f"{account_id}@{project}.iam.gserviceaccount.com"
        full = f"projects/{project}/serviceAccounts/{email}"
        if full in self.data.service_accounts:
            raise GcpAlreadyExists(f"service account '{full}' already exists")
        self.resource_manager.ensure_project(project)
        sa = ServiceAccount(
            name=full,
            email=email,
            unique_id=self.data.next_unique_id(),
            display_name=display_name,
        )
        self.data.service_accounts[full] = sa
        return sa

    def get_service_account(self, full_name: str) -> ServiceAccount:
        sa = self.data.service_accounts.get(full_name)
        if sa is None:
            raise GcpNotFound(f"service account '{full_name}' not found")
        return sa

    def list_service_accounts(self, project: str) -> list[ServiceAccount]:
        prefix = f"projects/{project}/serviceAccounts/"
        return [s for s in self.data.service_accounts.values() if s.name.startswith(prefix)]

    def delete_service_account(self, full_name: str) -> None:
        if full_name not in self.data.service_accounts:
            raise GcpNotFound(f"service account '{full_name}' not found")
        del self.data.service_accounts[full_name]

    # --- token mint (HS256 mock JWT) ---
    def mint_access_token(self, *, audience: str = "https://www.googleapis.com/", scope: str = "", email: str | None = None, expires_in: int = 3600) -> dict[str, Any]:
        now = int(datetime.datetime.now(datetime.UTC).timestamp())
        header = {"alg": "HS256", "typ": "JWT", "kid": "localstack-gcp"}
        payload = {
            "iss": email or "localstack@localstack.iam.gserviceaccount.com",
            "sub": email or "localstack@localstack.iam.gserviceaccount.com",
            "aud": audience,
            "iat": now,
            "exp": now + expires_in,
            "scope": scope,
            "jti": secrets.token_hex(8),
        }
        header_b64 = _b64url(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
        payload_b64 = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
        signing_input = f"{header_b64}.{payload_b64}".encode()
        signature = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
        sig_b64 = _b64url(signature)
        token = f"{header_b64}.{payload_b64}.{sig_b64}"
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "scope": scope,
        }

    def validate_grant(self, grant_type: str, payload: dict[str, Any]) -> None:
        if grant_type not in (
            "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_credentials",
            "refresh_token",
        ):
            raise GcpInvalidRequest(f"unsupported grant_type: {grant_type}")
        # mock: don't validate JWT signature; just require an 'assertion' or 'client_id'
        if grant_type == "urn:ietf:params:oauth:grant-type:jwt-bearer" and not payload.get("assertion"):
            raise GcpInvalidRequest("assertion required for jwt-bearer grant")
