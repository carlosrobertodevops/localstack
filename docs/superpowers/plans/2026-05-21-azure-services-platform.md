# Azure Services Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align this repository with the existing LocalStack for Azure alpha product, then incorporate or extend Azure emulator functionality only where the official implementation or behavior is missing.

**Architecture:** Treat Azure as an already-existing LocalStack product surface, not a greenfield clone of the AWS runtime. First inventory the official Azure alpha image and documented behavior, then decide whether to port upstream/private implementation, add an isolated `localstack-core/localstack/azure` domain, or only add tests/docs around the external image.

**Tech Stack:** Python, pytest, Docker, `localstack/localstack-azure-alpha`, `LOCALSTACK_AUTH_TOKEN`, `azlocal`, `azdlocal`, Terraform `azurerm` provider with `metadata_host`, LocalStack snapshot tooling, Azure CLI behavior, and LocalStack gateway patterns.

---

## Current Verdict

The original plan assumed we needed to build Azure support from scratch under `localstack-core/localstack/azure`. Official docs at `https://docs.localstack.cloud/azure/` show that LocalStack for Azure already exists as an alpha emulator with a Docker image, CLI integration, Terraform integration, and a documented service list.

Correct strategy now:

- Do not start by building a new Azure emulator from scratch.
- First find the source of the existing Azure alpha implementation.
- If the implementation is in another branch, private package, or image-only artifact, align this repo with that source.
- If source is not available, use `localstack/localstack-azure-alpha` as the behavior oracle and implement only confirmed gaps.
- Preserve existing AWS behavior. Azure work must not regress `localstack-core/localstack/aws`.

Local repo check at plan time:

- No `localstack-core/localstack/azure` path exists in this checkout.
- No `tests/azure` path exists in this checkout.
- Existing Azure references are incidental plus this plan file.

## Official LocalStack Azure Baseline

Sources:

- `https://docs.localstack.cloud/azure/`
- `https://docs.localstack.cloud/azure/getting-started/`
- `https://docs.localstack.cloud/azure/getting-started/quickstart/`
- `https://docs.localstack.cloud/azure/services/`
- `https://docs.localstack.cloud/azure/integrations/az/`
- `https://docs.localstack.cloud/azure/integrations/terraform/`

Facts from docs:

- Docker image: `localstack/localstack-azure-alpha`
- Auth requirement: `LOCALSTACK_AUTH_TOKEN`
- Main port: `4566`
- `latest` tag is nightly.
- Since the end-of-March 2026 release, versioned Azure image tags use calendar versioning: `YYYY.MM.patch`, for example `2026.03.0`.
- `azlocal` wraps Azure CLI and redirects commands to LocalStack.
- `azdlocal` wraps Azure Developer CLI and redirects deployments to LocalStack.
- Terraform uses `metadata_host = "localhost.localstack.cloud:4566"` in the `azurerm` provider.
- Storage endpoint suffix uses `core.azure.localhost.localstack.cloud:4566`.

Official start commands:

```bash
docker pull localstack/localstack-azure-alpha
```

```bash
export LOCALSTACK_AUTH_TOKEN=<your_auth_token>
IMAGE_NAME=localstack/localstack-azure-alpha localstack start
```

```bash
docker run \
  --rm -it \
  -p 4566:4566 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/.localstack/volume:/var/lib/localstack \
  -e LOCALSTACK_AUTH_TOKEN=${LOCALSTACK_AUTH_TOKEN:?} \
  localstack/localstack-azure-alpha
```

Official Docker Compose shape:

```yaml
version: "3.8"

services:
  localstack:
    container_name: "localstack-main"
    image: localstack/localstack-azure-alpha
    ports:
      - "127.0.0.1:4566:4566"
    environment:
      - LOCALSTACK_AUTH_TOKEN=${LOCALSTACK_AUTH_TOKEN:?}
    volumes:
      - "./volume:/var/lib/localstack"
```

## Official Tooling Baseline

Install LocalStack Azure CLI wrappers:

```bash
pip install azlocal
```

Docs list these wrappers:

| Original tool | LocalStack wrapper | Purpose                       |
| ------------- | ------------------ | ----------------------------- |
| `az`          | `azlocal`          | Interact with Azure resources |
| `azd`         | `azdlocal`         | Deploy ARM/Bicep templates    |

Azure CLI interception commands appear in docs with both hyphen and underscore forms. Test both because docs currently show both spellings:

```bash
azlocal start-interception
azlocal stop-interception
```

```bash
azlocal start_interception
azlocal stop_interception
```

Resource group smoke flow from docs:

```bash
azlocal start-interception
az group create --name myResourceGroup --location westeurope
az group show --name myResourceGroup
azlocal group list
az group delete --name myResourceGroup --yes
azlocal stop-interception
```

Terraform baseline from docs:

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=4.14.0"
    }
  }
}

provider "azurerm" {
  features {}

  subscription_id = "00000000-0000-0000-0000-000000000000"
  metadata_host   = "localhost.localstack.cloud:4566"
}
```

```hcl
resource "random_uuid" "uuid" {}

resource "azurerm_resource_group" "rg" {
  name     = "rg-hello-tf-${random_uuid.uuid.result}"
  location = "westeurope"
}
```

```bash
terraform init
terraform apply
az group list
```

## Official Service Inventory

The docs list these Azure service pages. This list is now the baseline for any coverage matrix:

| Service                                 | Docs slug                |
| --------------------------------------- | ------------------------ |
| Action Group                            | `action-group`           |
| API Management                          | `api-management`         |
| App Services                            | `web-app`                |
| Application Insights                    | `application-insights`   |
| Autoscale Setting                       | `autoscale-setting`      |
| Bastion Host                            | `bastion-host`           |
| Blob Storage                            | `blob-storage`           |
| Container Instances                     | `container-instance`     |
| Container Registry                      | `container-registry`     |
| Cosmos DB                               | `cosmos-db`              |
| Data Collection Rules                   | `data-collection-rules`  |
| Database for PostgreSQL Flexible Server | `dbfor-postgresql`       |
| Diagnostic Setting                      | `diagnostic-setting`     |
| Event Grid                              | `event-grid`             |
| Event Grid Data Plane                   | `event-grid-data-plane`  |
| Front Door                              | `front-door`             |
| Function Apps                           | `functions-app`          |
| Key Vault                               | `key-vault`              |
| Log Analytics                           | `log-analytics`          |
| Managed Identity                        | `managed-identity`       |
| Metric Alert                            | `metric-alert`           |
| Monitor                                 | `monitor`                |
| NAT Gateway                             | `nat-gateway`            |
| Network Interface                       | `network-interface`      |
| Private DNS Zone                        | `private-dns-zone`       |
| Private Endpoint                        | `private-endpoint`       |
| Public IP Address                       | `public-ip-address`      |
| Public IP Prefix                        | `public-ip-prefix`       |
| Queue Storage                           | `queue-storage`          |
| Resource Graph                          | `resource-graph`         |
| Resource Manager                        | `resource-manager`       |
| Role Assignment                         | `role-assignment`        |
| Role Definition                         | `role-definition`        |
| Route Table                             | `route-table`            |
| Scheduled Query Rules                   | `scheduled-query-rules`  |
| Service Bus                             | `service-bus`            |
| Service Bus Data Plane                  | `service-bus-data-plane` |
| SQL Database                            | `sql`                    |
| Storage Account                         | `storage-accounts`       |
| Table Storage                           | `table-storage`          |
| Virtual Network                         | `virtual-network`        |
| Web Test                                | `web-test`               |
| Workbook                                | `workbook`               |

## Non-Goals

- Do not duplicate the official Azure alpha implementation without first finding its source or behavior contract.
- Do not add Azure tests under `tests/aws/**`.
- Do not use AWS markers for Azure tests, even temporarily.
- Do not edit generated AWS API files under `localstack-core/localstack/aws/api/**`.
- Do not edit `*.snapshot.json` or `*.validation.json` manually.
- Do not treat Cosmos DB, Event Grid, Service Bus, Key Vault, or Function Apps as out of scope merely because the old plan did. They are documented services and must be classified by coverage.
- Do not ship a new `localstack-core/localstack/azure` framework if the existing alpha implementation can be incorporated or referenced instead.

## Architecture Decision Framework

Use this decision tree after discovery:

```text
Can we access the official Azure alpha implementation source?
  yes -> port/incorporate source-compatible modules into this repo
  no  -> use localstack/localstack-azure-alpha as behavior oracle

Does this repo need runtime Azure support, not just tests/docs?
  yes -> add isolated localstack-core/localstack/azure domain aligned with alpha behavior
  no  -> add tests/docs/tooling around external alpha image

Does a service already work in the alpha image?
  yes -> write coverage tests and docs, do not reimplement
  no  -> implement a focused gap with parity tests
```

Target package only if source is absent and runtime support is required:

```text
localstack-core/localstack/azure/
  __init__.py
  api/
  handlers/
  protocol/
  services/
  testing/
```

Test package:

```text
tests/azure/
  conftest.py
  services/
  integrations/
  snapshots/
```

## Rollout Phases

### Phase 1: Discover Existing Azure Implementation

Find where the official Azure alpha code lives: branch, private package, Pro module, Docker layer, artifact, or separate repository. Produce an inventory before coding.

### Phase 2: Establish Behavior Oracle

Run `localstack/localstack-azure-alpha` and verify documented flows with `azlocal`, `azdlocal`, Terraform, and direct endpoints.

### Phase 3: Build Coverage Matrix

For every documented service, classify support as `documented-only`, `works-in-alpha`, `partially-working`, `missing`, or `unknown`.

### Phase 4: Add Test Infrastructure

Create `tests/azure/**`, Azure markers, fixture patterns, and smoke tests. Keep AWS test infrastructure untouched.

### Phase 5: Incorporate Or Extend Runtime

Only after discovery, either port the official source or add a local Azure domain for confirmed gaps.

### Phase 6: CI And Docs

Add local alpha-image smoke tests and optional real Azure parity tests. Document exact commands for developers.

---

## Task 1: Source And Artifact Discovery

**Files:**

- Create: `docs/superpowers/plans/azure-discovery/source-inventory.md`
- Read: `pyproject.toml`
- Read: `Makefile`
- Read: `.github/workflows/**`

- [ ] **Step 1: Search repo for Azure source paths**

Run:

```bash
python - <<'PY'
from pathlib import Path
matches = []
for p in Path('.').rglob('*'):
    if '.git' in p.parts:
        continue
    name = p.name.lower()
    if 'azure' in name or 'azlocal' in name or 'azdlocal' in name:
        matches.append(str(p))
for item in matches:
    print(item)
print(f'TOTAL={len(matches)}')
PY
```

Expected: prints every local Azure-named path and a `TOTAL=` line. At plan time this repo had no `localstack-core/localstack/azure` and no `tests/azure`.

- [ ] **Step 2: Search package metadata for Azure extras**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in ['pyproject.toml', 'Makefile']:
    text = Path(path).read_text()
    hits = [line for line in text.splitlines() if 'azure' in line.lower() or 'azlocal' in line.lower()]
    print(f'## {path}')
    print('\n'.join(hits) if hits else '<no azure references>')
PY
```

Expected: either concrete references or `<no azure references>` per file.

- [ ] **Step 3: Write source inventory**

Create `docs/superpowers/plans/azure-discovery/source-inventory.md` with this exact structure:

```markdown
# Azure Source Inventory

## Local Repository Findings

- `localstack-core/localstack/azure`: present|absent
- `tests/azure`: present|absent
- Azure package extras: present|absent
- Azure CI workflows: present|absent

## External Artifact Findings

- Docker image: `localstack/localstack-azure-alpha`
- Requires: `LOCALSTACK_AUTH_TOKEN`
- Port: `4566`
- Tags: `latest` nightly, versioned tags `YYYY.MM.patch`

## Decision

- Source access: accessible|not-accessible|unknown
- Runtime strategy: port-official-source|external-alpha-tests-only|local-domain-gap-implementation
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/azure-discovery/source-inventory.md
git commit -m "docs(azure): inventory azure source availability"
```

## Task 2: Azure Alpha Docker Smoke Test

**Files:**

- Create: `tests/azure/integrations/test_azure_alpha_container.py`
- Create: `tests/azure/conftest.py`
- Create: `docs/superpowers/plans/azure-discovery/alpha-smoke.md`

- [ ] **Step 1: Add marker convention in `tests/azure/conftest.py`**

```python
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "azure_alpha: tests requiring localstack/localstack-azure-alpha")
    config.addinivalue_line("markers", "azure_local: tests running only against local Azure emulator")
```

- [ ] **Step 2: Add container preflight test**

```python
import os

import pytest


@pytest.mark.azure_alpha
def test_azure_alpha_auth_token_is_configured():
    assert os.environ.get("LOCALSTACK_AUTH_TOKEN"), "LOCALSTACK_AUTH_TOKEN is required for localstack-azure-alpha"
```

- [ ] **Step 3: Document manual smoke command**

Write `docs/superpowers/plans/azure-discovery/alpha-smoke.md`:

````markdown
# Azure Alpha Smoke

Start the alpha emulator:

```bash
export LOCALSTACK_AUTH_TOKEN=<your_auth_token>
IMAGE_NAME=localstack/localstack-azure-alpha localstack start
```

Alternative Docker run:

```bash
docker run \
  --rm -it \
  -p 4566:4566 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/.localstack/volume:/var/lib/localstack \
  -e LOCALSTACK_AUTH_TOKEN=${LOCALSTACK_AUTH_TOKEN:?} \
  localstack/localstack-azure-alpha
```
````

- [ ] **Step 4: Run preflight**

Run:

```bash
LOCALSTACK_AUTH_TOKEN=test python -m pytest tests/azure/integrations/test_azure_alpha_container.py -v
```

Expected: PASS for preflight only. This does not prove the Docker image is running.

- [ ] **Step 5: Commit**

```bash
git add tests/azure docs/superpowers/plans/azure-discovery/alpha-smoke.md
git commit -m "test(azure): add alpha container preflight"
```

## Task 3: azlocal CLI Smoke Test

**Files:**

- Create: `tests/azure/integrations/test_azlocal_smoke.py`
- Create: `docs/superpowers/plans/azure-discovery/azlocal-smoke.md`

- [ ] **Step 1: Add CLI availability test**

```python
import shutil
import subprocess

import pytest


@pytest.mark.azure_alpha
def test_azlocal_is_available():
    assert shutil.which("azlocal"), "Install with: pip install azlocal"


@pytest.mark.azure_alpha
def test_az_cli_is_available():
    assert shutil.which("az"), "Azure CLI must be installed for azlocal smoke tests"
```

- [ ] **Step 2: Add resource group command test behind explicit env**

```python
import os
import subprocess

import pytest


@pytest.mark.azure_alpha
def test_azlocal_resource_group_lifecycle():
    if os.environ.get("AZURE_ALPHA_LIVE_TEST") != "1":
        pytest.skip("set AZURE_ALPHA_LIVE_TEST=1 with localstack-azure-alpha running")

    name = "ls-rg-smoke"
    subprocess.run(["azlocal", "start-interception"], check=True)
    try:
        subprocess.run(["az", "group", "create", "--name", name, "--location", "westeurope"], check=True)
        subprocess.run(["az", "group", "show", "--name", name], check=True)
        subprocess.run(["azlocal", "group", "list"], check=True)
        subprocess.run(["az", "group", "delete", "--name", name, "--yes"], check=True)
    finally:
        subprocess.run(["azlocal", "stop-interception"], check=False)
```

- [ ] **Step 3: Document both interception spellings**

Write `docs/superpowers/plans/azure-discovery/azlocal-smoke.md`:

````markdown
# azlocal Smoke

Docs show both spellings. Verify both before standardizing tests:

```bash
azlocal start-interception
azlocal stop-interception
azlocal start_interception
azlocal stop_interception
```

Live smoke:

```bash
AZURE_ALPHA_LIVE_TEST=1 python -m pytest tests/azure/integrations/test_azlocal_smoke.py -v
```
````

- [ ] **Step 4: Run non-live checks**

Run:

```bash
python -m pytest tests/azure/integrations/test_azlocal_smoke.py -k "is_available" -v
```

Expected: PASS if `az` and `azlocal` are installed. FAIL message tells exact install gap.

- [ ] **Step 5: Commit**

```bash
git add tests/azure/integrations/test_azlocal_smoke.py docs/superpowers/plans/azure-discovery/azlocal-smoke.md
git commit -m "test(azure): add azlocal smoke tests"
```

## Task 4: Terraform Integration Smoke Test

**Files:**

- Create: `tests/azure/terraform/resource-group/provider.tf`
- Create: `tests/azure/terraform/resource-group/main.tf`
- Create: `tests/azure/integrations/test_terraform_azure.py`

- [ ] **Step 1: Add Terraform provider config**

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=4.14.0"
    }
  }
}

provider "azurerm" {
  features {}

  subscription_id = "00000000-0000-0000-0000-000000000000"
  metadata_host   = "localhost.localstack.cloud:4566"
}
```

- [ ] **Step 2: Add Terraform resource group config**

```hcl
resource "random_uuid" "uuid" {}

resource "azurerm_resource_group" "rg" {
  name     = "rg-hello-tf-${random_uuid.uuid.result}"
  location = "westeurope"
}
```

- [ ] **Step 3: Add live Terraform test**

```python
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.azure_alpha
def test_terraform_resource_group_smoke():
    if os.environ.get("AZURE_ALPHA_TERRAFORM_TEST") != "1":
        pytest.skip("set AZURE_ALPHA_TERRAFORM_TEST=1 with localstack-azure-alpha running")
    assert shutil.which("terraform"), "terraform must be installed"

    cwd = Path(__file__).parents[1] / "terraform" / "resource-group"
    subprocess.run(["terraform", "init", "-input=false"], cwd=cwd, check=True)
    subprocess.run(["terraform", "apply", "-auto-approve", "-input=false"], cwd=cwd, check=True)
```

- [ ] **Step 4: Run test only when alpha is running**

Run:

```bash
AZURE_ALPHA_TERRAFORM_TEST=1 python -m pytest tests/azure/integrations/test_terraform_azure.py -v
```

Expected: PASS if Docker alpha and Terraform are ready.

- [ ] **Step 5: Commit**

```bash
git add tests/azure/terraform tests/azure/integrations/test_terraform_azure.py
git commit -m "test(azure): add terraform metadata_host smoke"
```

## Task 5: Service Coverage Matrix

**Files:**

- Create: `docs/superpowers/plans/azure-discovery/service-coverage.md`
- Create: `scripts/azure_service_coverage.py`

- [ ] **Step 1: Add static service list script**

```python
SERVICES = [
    ("Action Group", "action-group"),
    ("API Management", "api-management"),
    ("App Services", "web-app"),
    ("Application Insights", "application-insights"),
    ("Autoscale Setting", "autoscale-setting"),
    ("Bastion Host", "bastion-host"),
    ("Blob Storage", "blob-storage"),
    ("Container Instances", "container-instance"),
    ("Container Registry", "container-registry"),
    ("Cosmos DB", "cosmos-db"),
    ("Data Collection Rules", "data-collection-rules"),
    ("Database for PostgreSQL Flexible Server", "dbfor-postgresql"),
    ("Diagnostic Setting", "diagnostic-setting"),
    ("Event Grid", "event-grid"),
    ("Event Grid Data Plane", "event-grid-data-plane"),
    ("Front Door", "front-door"),
    ("Function Apps", "functions-app"),
    ("Key Vault", "key-vault"),
    ("Log Analytics", "log-analytics"),
    ("Managed Identity", "managed-identity"),
    ("Metric Alert", "metric-alert"),
    ("Monitor", "monitor"),
    ("NAT Gateway", "nat-gateway"),
    ("Network Interface", "network-interface"),
    ("Private DNS Zone", "private-dns-zone"),
    ("Private Endpoint", "private-endpoint"),
    ("Public IP Address", "public-ip-address"),
    ("Public IP Prefix", "public-ip-prefix"),
    ("Queue Storage", "queue-storage"),
    ("Resource Graph", "resource-graph"),
    ("Resource Manager", "resource-manager"),
    ("Role Assignment", "role-assignment"),
    ("Role Definition", "role-definition"),
    ("Route Table", "route-table"),
    ("Scheduled Query Rules", "scheduled-query-rules"),
    ("Service Bus", "service-bus"),
    ("Service Bus Data Plane", "service-bus-data-plane"),
    ("SQL Database", "sql"),
    ("Storage Account", "storage-accounts"),
    ("Table Storage", "table-storage"),
    ("Virtual Network", "virtual-network"),
    ("Web Test", "web-test"),
    ("Workbook", "workbook"),
]


def main():
    print("| Service | Docs URL | Status | Evidence |")
    print("| --- | --- | --- | --- |")
    for name, slug in SERVICES:
        print(f"| {name} | https://docs.localstack.cloud/azure/services/{slug}/ | unknown | not tested yet |")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate coverage matrix**

Run:

```bash
python scripts/azure_service_coverage.py > docs/superpowers/plans/azure-discovery/service-coverage.md
```

Expected: markdown table with every documented Azure service and `unknown` status.

- [ ] **Step 3: Commit**

```bash
git add scripts/azure_service_coverage.py docs/superpowers/plans/azure-discovery/service-coverage.md
git commit -m "docs(azure): add service coverage matrix"
```

## Task 6: Resource Manager Coverage Audit

**Files:**

- Create: `tests/azure/services/resource_manager/test_resource_groups.py`
- Create: `docs/superpowers/plans/azure-discovery/resource-manager-coverage.md`

- [ ] **Step 1: Add LocalStack alpha test for resource group shape**

```python
import json
import os
import subprocess

import pytest


@pytest.mark.azure_alpha
def test_resource_group_shape_matches_docs():
    if os.environ.get("AZURE_ALPHA_LIVE_TEST") != "1":
        pytest.skip("set AZURE_ALPHA_LIVE_TEST=1 with localstack-azure-alpha running")

    name = "ls-rg-shape"
    subprocess.run(["azlocal", "start-interception"], check=True)
    try:
        result = subprocess.run(
            ["az", "group", "create", "--name", name, "--location", "westeurope"],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        assert payload["name"] == name
        assert payload["location"] == "westeurope"
        assert payload["type"] == "Microsoft.Resources/resourceGroups"
        assert payload["properties"]["provisioningState"] == "Succeeded"
    finally:
        subprocess.run(["az", "group", "delete", "--name", name, "--yes"], check=False)
        subprocess.run(["azlocal", "stop-interception"], check=False)
```

- [ ] **Step 2: Record coverage evidence**

Write `docs/superpowers/plans/azure-discovery/resource-manager-coverage.md`:

```markdown
# Resource Manager Coverage

## Commands Tested

- `az group create --name ls-rg-shape --location westeurope`
- `az group show --name ls-rg-shape`
- `azlocal group list`
- `az group delete --name ls-rg-shape --yes`

## Expected Shape

- `id`: `/subscriptions/<generated>/resourceGroups/<name>`
- `location`: requested location
- `name`: requested name
- `properties.provisioningState`: `Succeeded`
- `type`: `Microsoft.Resources/resourceGroups`
```

- [ ] **Step 3: Run live test**

Run:

```bash
AZURE_ALPHA_LIVE_TEST=1 python -m pytest tests/azure/services/resource_manager/test_resource_groups.py -v
```

Expected: PASS if alpha image and `azlocal` are working.

- [ ] **Step 4: Commit**

```bash
git add tests/azure/services/resource_manager docs/superpowers/plans/azure-discovery/resource-manager-coverage.md
git commit -m "test(azure): audit resource manager coverage"
```

## Task 7: Storage Endpoint Compatibility Audit

**Files:**

- Create: `tests/azure/services/storage/test_storage_endpoints.py`
- Create: `docs/superpowers/plans/azure-discovery/storage-endpoints.md`

- [ ] **Step 1: Add endpoint suffix unit test**

```python
def test_storage_endpoint_suffixes_match_docs():
    account = "stordoc86acct"

    assert f"https://{account}.blob.core.azure.localhost.localstack.cloud:4566".endswith(
        ".blob.core.azure.localhost.localstack.cloud:4566"
    )
    assert f"https://{account}.queue.core.azure.localhost.localstack.cloud:4566".endswith(
        ".queue.core.azure.localhost.localstack.cloud:4566"
    )
    assert f"https://{account}.table.core.azure.localhost.localstack.cloud:4566".endswith(
        ".table.core.azure.localhost.localstack.cloud:4566"
    )
    assert f"https://{account}.file.core.azure.localhost.localstack.cloud:4566".endswith(
        ".file.core.azure.localhost.localstack.cloud:4566"
    )
```

- [ ] **Step 2: Document storage endpoint contract**

Write `docs/superpowers/plans/azure-discovery/storage-endpoints.md`:

````markdown
# Storage Endpoint Contract

LocalStack Azure docs use this suffix:

```text
core.azure.localhost.localstack.cloud:4566
```

Service endpoints:

```text
https://<account>.blob.core.azure.localhost.localstack.cloud:4566
https://<account>.queue.core.azure.localhost.localstack.cloud:4566
https://<account>.table.core.azure.localhost.localstack.cloud:4566
https://<account>.file.core.azure.localhost.localstack.cloud:4566
```
````

- [ ] **Step 3: Run endpoint contract test**

Run:

```bash
python -m pytest tests/azure/services/storage/test_storage_endpoints.py -v
```

Expected: PASS without Docker.

- [ ] **Step 4: Commit**

```bash
git add tests/azure/services/storage/test_storage_endpoints.py docs/superpowers/plans/azure-discovery/storage-endpoints.md
git commit -m "test(azure): document storage endpoint contract"
```

## Task 8: Gap Implementation Gate

**Files:**

- Create: `docs/superpowers/plans/azure-discovery/gap-decision.md`

- [ ] **Step 1: Classify source access**

Write one of these exact decisions in `gap-decision.md`:

```markdown
# Azure Gap Decision

## Decision

Use official source port.

## Reason

The Azure alpha implementation source is accessible and should be incorporated instead of recreated.
```

or:

```markdown
# Azure Gap Decision

## Decision

Use alpha image as behavior oracle.

## Reason

The Azure alpha implementation source is not accessible from this checkout, so tests will target `localstack/localstack-azure-alpha` and local runtime work will implement only confirmed gaps.
```

or:

```markdown
# Azure Gap Decision

## Decision

Defer runtime implementation.

## Reason

Current need is tests and docs around the existing alpha image, not new runtime code in this repository.
```

- [ ] **Step 2: Choose runtime path**

If decision is `Use official source port`, create porting tasks from the source tree names.

If decision is `Use alpha image as behavior oracle`, create only missing `localstack-core/localstack/azure` files after a failing alpha-vs-local gap test exists.

If decision is `Defer runtime implementation`, do not create `localstack-core/localstack/azure`.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/azure-discovery/gap-decision.md
git commit -m "docs(azure): record azure runtime decision"
```

## Task 9: Azure Marker And Snapshot Infrastructure

**Files:**

- Create: `localstack-core/localstack/testing/azure/__init__.py`
- Create: `localstack-core/localstack/testing/azure/util.py`
- Create: `localstack-core/localstack/testing/pytest/azure/__init__.py`
- Create: `localstack-core/localstack/testing/pytest/azure/marking.py`
- Create: `localstack-core/localstack/testing/pytest/azure/fixtures.py`
- Modify: `tests/azure/conftest.py`
- Test: `tests/unit/testing/test_azure_testing_util.py`

- [ ] **Step 1: Add Azure target utility test**

```python
from localstack.tooling.testing.azure.util import is_azure_alpha, is_azure_cloud


def test_azure_alpha_target(monkeypatch):
    monkeypatch.setenv("TEST_TARGET", "AZURE_ALPHA")

    assert is_azure_alpha()
    assert not is_azure_cloud()


def test_azure_cloud_target(monkeypatch):
    monkeypatch.setenv("TEST_TARGET", "AZURE_CLOUD")

    assert is_azure_cloud()
    assert not is_azure_alpha()
```

- [ ] **Step 2: Add target utilities**

```python
import os


def is_azure_alpha() -> bool:
    return os.environ.get("TEST_TARGET") == "AZURE_ALPHA"


def is_azure_cloud() -> bool:
    return os.environ.get("TEST_TARGET") == "AZURE_CLOUD"
```

- [ ] **Step 3: Add Azure marker constants**

```python
AZURE_ALPHA = "azure_alpha"
AZURE_LOCAL = "azure_local"
AZURE_CLOUD_VALIDATED = "azure_cloud_validated"
AZURE_NEEDS_FIXING = "azure_needs_fixing"
```

- [ ] **Step 4: Run marker utility tests**

Run:

```bash
python -m pytest tests/unit/testing/test_azure_testing_util.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add localstack-core/localstack/testing/azure localstack-core/localstack/testing/pytest/azure tests/azure/conftest.py tests/unit/testing/test_azure_testing_util.py
git commit -m "test(azure): add azure marker infrastructure"
```

## Task 10: CI Strategy For Azure Alpha

**Files:**

- Create: `.github/workflows/azure-alpha-smoke.yml`
- Create: `docs/superpowers/plans/azure-discovery/ci-strategy.md`

- [ ] **Step 1: Add manual workflow**

```yaml
name: Azure Alpha Smoke

on:
  workflow_dispatch:

jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install test dependencies
        run: make install-test
      - name: Install Azure CLI wrapper
        run: . .venv/bin/activate && pip install azlocal
      - name: Run non-live Azure tests
        run: . .venv/bin/activate && python -m pytest tests/azure -m "not azure_alpha" -v
```

- [ ] **Step 2: Document why live alpha is not default PR gate**

Write `docs/superpowers/plans/azure-discovery/ci-strategy.md`:

````markdown
# Azure CI Strategy

`localstack/localstack-azure-alpha` requires `LOCALSTACK_AUTH_TOKEN`, so live alpha tests are manual or scheduled first.

Default PR gate:

```bash
python -m pytest tests/azure -m "not azure_alpha" -v
```

Manual live gate:

```bash
LOCALSTACK_AUTH_TOKEN=<token> AZURE_ALPHA_LIVE_TEST=1 python -m pytest tests/azure -m azure_alpha -v
```
````

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/azure-alpha-smoke.yml docs/superpowers/plans/azure-discovery/ci-strategy.md
git commit -m "ci(azure): add manual azure alpha smoke workflow"
```

## Testing Strategy

- Non-live tests can run on PRs without Docker alpha.
- Live alpha tests require `LOCALSTACK_AUTH_TOKEN` and explicit env flags.
- Real Azure cloud parity uses `TEST_TARGET=AZURE_CLOUD` and service principal credentials only after alpha behavior is stable.
- Do not use AWS markers in Azure tests.
- Do not edit snapshots manually.
- Prefer `azlocal` and Terraform smoke tests before designing Python SDK fixtures.

## Updated Risks

- Official Azure alpha source may not be available in this checkout.
- Docs may be ahead of source code or alpha image behavior.
- `azlocal` docs show both `start-interception` and `start_interception`; tests must establish canonical command.
- Terraform `metadata_host` is essential; missing it can target real Azure.
- `LOCALSTACK_AUTH_TOKEN` makes live CI opt-in.
- Building `localstack-core/localstack/azure` without source alignment risks incompatible duplicate architecture.

## Updated Open Decisions

- Where is the official Azure alpha source stored?
- Should this repo include Azure runtime code or only tests/docs against the alpha image?
- Which services in `/azure/services/` work in the current alpha image?
- Which service gaps are worth implementing locally first?
- What is the canonical `azlocal` interception command spelling for our tests?

## Completion Criteria

- `docs/superpowers/plans/azure-discovery/source-inventory.md` records source availability.
- `localstack/localstack-azure-alpha` start flow is documented and tested by preflight.
- `azlocal` resource group lifecycle has a live smoke test.
- Terraform `metadata_host` flow has a live smoke test.
- Service coverage matrix includes every service documented at `https://docs.localstack.cloud/azure/services/`.
- Runtime implementation decision is recorded before creating `localstack-core/localstack/azure`.
- Azure tests use Azure markers, not AWS markers.
- Existing AWS tests remain untouched.
