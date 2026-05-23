"""Unit tests for the host-side console CLI bridge validators.

The bridge HTTP layer needs aiohttp, but validators are pure stdlib and
can be tested independently.
"""

from __future__ import annotations

import pytest

from localstack.tooling.dev.console_bridge import (
    CLI_ALLOWLIST,
    build_env,
    cli_status,
    resolve_binary,
    validate_args,
    validate_cli,
    validate_env,
)


class TestValidateCli:
    @pytest.mark.parametrize("cli", CLI_ALLOWLIST)
    def test_allows_known(self, cli):
        validate_cli(cli)

    @pytest.mark.parametrize("cli", ["evil", "", "AWS", "rm", None, "aws ls"])
    def test_rejects_unknown(self, cli):
        with pytest.raises(ValueError):
            validate_cli(cli)


class TestValidateArgs:
    def test_clean(self):
        validate_args(["s3", "ls", "--region", "us-east-1"])

    def test_empty(self):
        validate_args([])

    @pytest.mark.parametrize(
        "bad",
        [
            ["s3", "ls", "; rm -rf /"],
            ["a", "&&"],
            ["a", "|cat"],
            ["a", "$(whoami)"],
            ["a", "`id`"],
            ["a", "ls\nrm"],
            ["a", "out > /etc"],
            ["a", "in < /etc"],
        ],
    )
    def test_metachars_rejected(self, bad):
        with pytest.raises(ValueError):
            validate_args(bad)

    def test_non_list_rejected(self):
        with pytest.raises(ValueError):
            validate_args("s3 ls")

    def test_non_string_element_rejected(self):
        with pytest.raises(ValueError):
            validate_args(["s3", 42])


class TestValidateEnv:
    def test_none(self):
        validate_env(None)

    def test_clean(self):
        validate_env({"AWS_REGION": "us-east-1", "FOO_BAR": "baz"})

    @pytest.mark.parametrize("key", ["bad-key", "1KEY", "lower", "k ey", "BAD;KEY"])
    def test_bad_key_rejected(self, key):
        with pytest.raises(ValueError):
            validate_env({key: "v"})

    def test_metachar_value_rejected(self):
        with pytest.raises(ValueError):
            validate_env({"FOO": "ok; rm -rf"})

    def test_non_dict_rejected(self):
        with pytest.raises(ValueError):
            validate_env([("FOO", "BAR")])


class TestEnvBuilder:
    def test_aws_defaults(self):
        env = build_env("aws", None)
        assert env["AWS_ACCESS_KEY_ID"] == "test"
        assert env["AWS_SECRET_ACCESS_KEY"] == "test"
        assert env["AWS_ENDPOINT_URL"] == "http://localhost:4566"

    def test_aws_overrides_win(self):
        env = build_env("aws", {"AWS_REGION": "sa-east-1"})
        assert env["AWS_REGION"] == "sa-east-1"

    def test_user_overrides_default(self):
        env = build_env("aws", {"AWS_ENDPOINT_URL": "http://elsewhere:9999"})
        assert env["AWS_ENDPOINT_URL"] == "http://elsewhere:9999"

    def test_non_aws_no_aws_defaults(self):
        env = build_env("gcloud", None)
        assert "CLOUDSDK_CORE_PROJECT" not in env or env.get(
            "CLOUDSDK_CORE_PROJECT"
        ) == "localstack-project"


class TestResolveBinary:
    def test_known_cli_returns_path_or_none(self):
        # Just check that it doesn't crash and returns str or None.
        for cli in CLI_ALLOWLIST:
            result = resolve_binary(cli)
            assert result is None or isinstance(result, str)


def test_cli_status_returns_dict():
    status = cli_status()
    assert set(status).issuperset(set(CLI_ALLOWLIST))
    assert "terraform" in status
    for v in status.values():
        assert isinstance(v, bool)
