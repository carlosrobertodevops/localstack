from localstack.aws.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    ResourceProvider,
)


class LambdaVersionProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::Lambda::Version"

    def __init__(self):
        self.factory: type[ResourceProvider] | None = None

    def load(self):
        from localstack.aws.services.lambda_.resource_providers.aws_lambda_version import (
            LambdaVersionProvider,
        )

        self.factory = LambdaVersionProvider
