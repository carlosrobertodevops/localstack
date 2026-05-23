"""Unit tests for the console CLI + IaC passthrough endpoints.

See docs/multi-cloud-console-plan.md §7, §12.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from localstack.aws.services.internal import (
    CliPassthroughResource,
    IacApplyResource,
    IacPreviewResource,
    SessionLogResource,
    _terraform_provider_block,
    _validate_args,
    _validate_env,
)


def _make_request(body: dict) -> MagicMock:
    req = MagicMock()
    req.get_json.return_value = body
    return req


def _parse(response):
    if hasattr(response, "get_data"):
        return json.loads(response.get_data(as_text=True))
    return response


class TestValidators:
    @pytest.mark.parametrize(
        "args",
        [
            ["s3", "ls", "; rm -rf /"],
            ["s3", "ls", "&&", "touch", "x"],
            ["a", "$(whoami)"],
            ["a", "`whoami`"],
            ["a", "ls\nrm"],
            ["a", "out > /etc/passwd"],
        ],
    )
    def test_args_metachars_rejected(self, args):
        assert _validate_args(args) is not None

    def test_args_clean_accepted(self):
        assert _validate_args(["s3", "ls", "--region", "us-east-1"]) is None

    def test_args_non_list_rejected(self):
        assert _validate_args("s3 ls") is not None

    def test_args_non_string_element_rejected(self):
        assert _validate_args(["s3", 1]) is not None

    @pytest.mark.parametrize("key", ["bad-key", "1KEY", "key", "k ey", "BAD;KEY"])
    def test_env_key_rejected(self, key):
        assert _validate_env({key: "v"}) is not None

    def test_env_clean_accepted(self):
        assert _validate_env({"AWS_REGION": "us-east-1", "FOO_BAR": "baz"}) is None

    def test_env_metachar_value_rejected(self):
        assert _validate_env({"FOO": "ok; rm"}) is not None

    def test_env_none_accepted(self):
        assert _validate_env(None) is None


class TestCliPassthrough:
    def test_rejects_unknown_cli(self):
        res = CliPassthroughResource().on_post(_make_request({"cli": "evil", "args": []}))
        assert res.status_code == 400
        assert "allowlist" in _parse(res)["error"]

    def test_rejects_metachar_args(self):
        res = CliPassthroughResource().on_post(
            _make_request({"cli": "aws", "args": ["s3", "ls", "; rm -rf /"]})
        )
        assert res.status_code == 400

    def test_rejects_bad_env_key(self):
        res = CliPassthroughResource().on_post(
            _make_request({"cli": "aws", "args": ["s3"], "env": {"bad-key": "v"}})
        )
        assert res.status_code == 400

    def test_invalid_json_rejected(self):
        req = MagicMock()
        req.get_json.side_effect = ValueError("bad")
        res = CliPassthroughResource().on_post(req)
        assert res.status_code == 400


class TestIacEndpoints:
    def test_rejects_unknown_tool(self):
        res = IacApplyResource().on_post(
            _make_request({"tool": "ansible", "snippet": "", "action": "apply"})
        )
        assert res.status_code == 400

    def test_rejects_big_snippet(self):
        big = "x" * (65 * 1024)
        res = IacApplyResource().on_post(
            _make_request({"tool": "terraform", "snippet": big, "action": "plan"})
        )
        assert res.status_code == 400

    def test_rejects_unknown_action(self):
        res = IacApplyResource().on_post(
            _make_request(
                {"tool": "terraform", "snippet": "resource {}", "action": "wipe"}
            )
        )
        assert res.status_code == 400

    def test_preview_returns_files_terraform(self):
        res = IacPreviewResource().on_post(
            _make_request(
                {
                    "tool": "terraform",
                    "snippet": 'resource "aws_s3_bucket" "x" { bucket = "x" }',
                }
            )
        )
        # success path returns a plain dict (Resource wraps it)
        assert isinstance(res, dict)
        assert res["tool"] == "terraform"
        assert "provider.tf" in res["files"]
        assert "main.tf" in res["files"]
        assert "localhost:4566" in res["files"]["provider.tf"]

    def test_preview_returns_files_serverless(self):
        res = IacPreviewResource().on_post(
            _make_request({"tool": "serverless", "snippet": "service: x\n"})
        )
        assert res["tool"] == "serverless"
        assert "serverless.yml" in res["files"]


class TestSessionLog:
    def test_path_traversal_blocked(self):
        res = SessionLogResource().on_get(
            MagicMock(), session_id="../../../../etc/passwd"
        )
        assert res.status_code == 404

    def test_invalid_session_id_blocked(self):
        res = SessionLogResource().on_get(MagicMock(), session_id="nothex")
        assert res.status_code == 404

    def test_missing_log_404(self):
        # Valid format, but no such session exists
        res = SessionLogResource().on_get(
            MagicMock(), session_id="a" * 32
        )
        assert res.status_code == 404


def test_provider_block_targets_localstack():
    block = _terraform_provider_block()
    assert "http://localhost:4566" in block
    assert "skip_credentials_validation = true" in block
    assert "s3_use_path_style           = true" in block
