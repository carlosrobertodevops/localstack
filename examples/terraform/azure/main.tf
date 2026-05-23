terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
  }
}

# The azurerm provider's `metadata_host` lets us route ARM calls at the
# LocalStack TLS sidecar. The provider still calls Entra for tokens; that
# is handled by our entra router on the same gateway.
#
# Auth via service principal env vars — no `az login` required:
#   export ARM_CLIENT_ID=00000000-0000-0000-0000-000000000001
#   export ARM_CLIENT_SECRET=test-secret
#   export ARM_TENANT_ID=localstack-tenant
#   export ARM_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000000
#   export ARM_METADATA_HOST=localhost:4569
#   export SSL_CERT_FILE=$(pwd)/../../../localstack-tls/certs/cert.pem
provider "azurerm" {
  features {}

  metadata_host = "localhost:4569"

  skip_provider_registration = true
  storage_use_azuread        = false

  # Use the env vars listed above for credentials.
}

resource "azurerm_resource_group" "demo" {
  name     = "tf-localstack-rg"
  location = "eastus"
}

resource "azurerm_storage_account" "demo" {
  name                     = "tflocalstackstor"
  resource_group_name      = azurerm_resource_group.demo.name
  location                 = azurerm_resource_group.demo.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "demo" {
  name                  = "demo"
  storage_account_name  = azurerm_storage_account.demo.name
  container_access_type = "private"
}

output "rg"               { value = azurerm_resource_group.demo.name }
output "storage_account"  { value = azurerm_storage_account.demo.name }
output "container"        { value = azurerm_storage_container.demo.name }
