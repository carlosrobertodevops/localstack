"""Smoke tests for the multi-cloud console HTTP endpoints.

These hit a running LocalStack edge gateway (default :4566) and verify
that the console-specific routes are wired up. They are skipped by
default because they require a live process — see the unit tests under
`tests/unit/console/` for pure validator coverage.

To run locally:

    docker compose up -d localstack
    SKIP_CONSOLE_SMOKE=0 pytest tests/aws/test_console_endpoints_smoke.py
"""

from __future__ import annotations

import os

import pytest
import requests

EDGE = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")
SKIP = os.environ.get("SKIP_CONSOLE_SMOKE", "1") != "0"

pytestmark = pytest.mark.skipif(
    SKIP, reason="set SKIP_CONSOLE_SMOKE=0 with a running LocalStack to run"
)


def test_clouds_list_returns_clouds_key():
    r = requests.get(f"{EDGE}/_localstack/clouds", timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert "clouds" in body
    assert isinstance(body["clouds"], list)


def test_console_iac_preview_returns_files():
    snippet = 'resource "aws_s3_bucket" "x" { bucket = "x" }'
    r = requests.post(
        f"{EDGE}/_localstack/console/iac/preview",
        json={"tool": "terraform", "snippet": snippet},
        timeout=5,
    )
    assert r.status_code == 200
    body = r.json()
    assert "files" in body
    assert "provider.tf" in body["files"]
    assert "main.tf" in body["files"]
    assert "localhost:4566" in body["files"]["provider.tf"]


def test_console_cli_rejects_unknown():
    r = requests.post(
        f"{EDGE}/_localstack/console/cli",
        json={"cli": "evil", "args": []},
        timeout=5,
    )
    assert r.status_code == 400


def test_console_iac_rejects_unknown_tool():
    r = requests.post(
        f"{EDGE}/_localstack/console/iac",
        json={"tool": "ansible", "snippet": "", "action": "apply"},
        timeout=5,
    )
    assert r.status_code == 400


def test_console_session_log_traversal_blocked():
    r = requests.get(
        f"{EDGE}/_localstack/console/sessions/..%2F..%2Fetc%2Fpasswd/log",
        timeout=5,
    )
    assert r.status_code == 404
