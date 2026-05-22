import os

import pytest
from _pytest.monkeypatch import MonkeyPatch

from localstack.platform import config
os.environ["LOCALSTACK_INTERNAL_TEST_RUN"] = "1"

pytest_plugins = [
    "localstack.tooling.testing.pytest.fixtures",
    "localstack.tooling.testing.pytest.container",
    "localstack_snapshot.pytest.snapshot",
    "localstack.tooling.testing.pytest.filters",
    "localstack.tooling.testing.pytest.fixture_conflicts",
    "localstack.tooling.testing.pytest.marking",
    "localstack.tooling.testing.pytest.marker_report",
    "localstack.tooling.testing.pytest.in_memory_localstack",
    "localstack.tooling.testing.pytest.validation_tracking",
    "localstack.tooling.testing.pytest.path_filter",
    "localstack.tooling.testing.pytest.stepfunctions.fixtures",
    "localstack.tooling.testing.pytest.cloudformation.fixtures",
]


@pytest.fixture(scope="session")
def aws_session():
    """
    This fixture returns the Boto Session instance for testing.
    """
    from localstack.tooling.testing.aws.util import base_aws_session

    return base_aws_session()


@pytest.fixture(scope="session")
def secondary_aws_session():
    """
    This fixture returns the Boto Session instance for testing a secondary account.
    """
    from localstack.tooling.testing.aws.util import secondary_aws_session

    return secondary_aws_session()


@pytest.fixture(scope="session")
def aws_client_factory(aws_session):
    """
    This fixture returns a client factory for testing.

    Use this fixture if you need to use custom endpoint or Boto config.
    """
    from localstack.tooling.testing.aws.util import base_aws_client_factory

    return base_aws_client_factory(aws_session)


@pytest.fixture(scope="session")
def secondary_aws_client_factory(secondary_aws_session):
    """
    This fixture returns a client factory for testing a secondary account.

    Use this fixture if you need to use custom endpoint or Boto config.
    """
    from localstack.tooling.testing.aws.util import base_aws_client_factory

    return base_aws_client_factory(secondary_aws_session)


@pytest.fixture(scope="session")
def aws_client(aws_client_factory):
    """
    This fixture can be used to obtain Boto clients for testing.

    The clients are configured with the primary testing credentials.
    """
    from localstack.tooling.testing.aws.util import base_testing_aws_client

    return base_testing_aws_client(aws_client_factory)


@pytest.fixture(scope="session")
def secondary_aws_client(secondary_aws_client_factory):
    """
    This fixture can be used to obtain Boto clients for testing a secondary account.

    The clients are configured with the secondary testing credentials.
    The region is not overridden.
    """
    from localstack.tooling.testing.aws.util import base_testing_aws_client

    return base_testing_aws_client(secondary_aws_client_factory)


@pytest.fixture(scope="session", autouse=True)
def enable_stack_trace_for_tests():
    """
    Ensure stack traces are enabled in HTTP responses during test sessions.

    This is useful for debugging purposes.
    """
    mpatch = MonkeyPatch()
    mpatch.setattr(config, "INCLUDE_STACK_TRACES_IN_HTTP_RESPONSE", True)
    yield mpatch
    mpatch.undo()
