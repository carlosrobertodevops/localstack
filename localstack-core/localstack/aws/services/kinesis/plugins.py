import localstack.platform.config as config
from localstack.tooling.packages import Package, package


@package(name="kinesis-mock")
def kinesismock_package() -> Package:
    from localstack.aws.services.kinesis.packages import (
        KinesisMockEngine,
        kinesismock_package,
        kinesismock_scala_package,
    )

    if KinesisMockEngine(config.KINESIS_MOCK_PROVIDER_ENGINE) == KinesisMockEngine.SCALA:
        return kinesismock_scala_package

    return kinesismock_package
