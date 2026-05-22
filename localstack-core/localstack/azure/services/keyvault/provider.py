"""Microsoft.KeyVault provider — ARM metadata + secret data plane (subset)."""

from __future__ import annotations

from localstack.azure.defaults import create_default_registry
from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.ids import AzureResourceId
from localstack.azure.resource_manager import ResourceManagerProvider
from localstack.azure.scope import AzureScope
from localstack.azure.services.keyvault.models import (
    KeyVaultDataPlaneStore,
    KeyVaultSecret,
    KeyVaultSecretVersion,
)
from localstack.azure.spec import AzureServiceSpec
from localstack.azure.stores import AzureGenericResource, AzureStores

NAMESPACE = "Microsoft.KeyVault"
RESOURCE_TYPE = "vaults"


class MicrosoftKeyVaultProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: AzureStores | None = None,
        data_store: KeyVaultDataPlaneStore | None = None,
    ) -> None:
        self.stores = stores or AzureStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(
            stores=self.stores, registry=create_default_registry()
        )
        self.resource_manager.registry.register(
            AzureServiceSpec(
                namespace=NAMESPACE,
                resource_type=RESOURCE_TYPE,
                api_versions=("7.4", "2023-07-01"),
                locations=("eastus", "westeurope", "westus2", "brazilsouth"),
            )
        )
        self.data_store = data_store or KeyVaultDataPlaneStore()

    # -- ARM metadata --

    def create_vault(
        self, scope: AzureScope, name: str, parameters: dict
    ) -> AzureGenericResource:
        resource = self.resource_manager.create_or_update_resource(
            scope, self._vault_id(scope, name), parameters
        )
        self.data_store.ensure_vault(name)
        return resource

    def get_vault(self, scope: AzureScope, name: str) -> AzureGenericResource:
        return self.resource_manager.get_resource(scope, self._vault_id(scope, name))

    def delete_vault(self, scope: AzureScope, name: str) -> None:
        self.resource_manager.delete_resource(scope, self._vault_id(scope, name))
        self.data_store.delete_vault(name)

    # -- secrets data plane --

    def set_secret(
        self,
        vault_name: str,
        secret_name: str,
        value: str,
        *,
        content_type: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> KeyVaultSecretVersion:
        if not value:
            raise AzureInvalidRequest("secret value must not be empty")
        vault = self.data_store.ensure_vault(vault_name)
        secret = vault.secrets.get(secret_name)
        if secret is None:
            secret = KeyVaultSecret(name=secret_name)
            vault.secrets[secret_name] = secret
        version = KeyVaultSecretVersion(
            value=value, content_type=content_type, tags=dict(tags or {})
        )
        secret.versions.append(version)
        return version

    def get_secret(
        self, vault_name: str, secret_name: str, *, version: str | None = None
    ) -> KeyVaultSecretVersion:
        vault = self.data_store.get_vault(vault_name)
        if vault is None:
            raise AzureNotFound(f"Key Vault not found: {vault_name}")
        secret = vault.secrets.get(secret_name)
        if secret is None:
            raise AzureNotFound(f"Key Vault secret not found: {secret_name}")
        if version is None:
            return secret.latest
        for v in secret.versions:
            if v.id == version:
                return v
        raise AzureNotFound(f"Key Vault secret version not found: {version}")

    def list_secrets(self, vault_name: str) -> list[KeyVaultSecret]:
        vault = self.data_store.get_vault(vault_name)
        if vault is None:
            raise AzureNotFound(f"Key Vault not found: {vault_name}")
        return sorted(vault.secrets.values(), key=lambda s: s.name.lower())

    def delete_secret(self, vault_name: str, secret_name: str) -> None:
        vault = self.data_store.get_vault(vault_name)
        if vault is None:
            raise AzureNotFound(f"Key Vault not found: {vault_name}")
        if vault.secrets.pop(secret_name, None) is None:
            raise AzureNotFound(f"Key Vault secret not found: {secret_name}")

    # -- helpers --

    @staticmethod
    def _vault_id(scope: AzureScope, name: str) -> AzureResourceId:
        if not scope.resource_group:
            raise AzureInvalidRequest("vault operations require a resource group in scope")
        return AzureResourceId.parse(
            f"/subscriptions/{scope.subscription_id}/resourceGroups/{scope.resource_group}/"
            f"providers/{NAMESPACE}/{RESOURCE_TYPE}/{name}"
        )
