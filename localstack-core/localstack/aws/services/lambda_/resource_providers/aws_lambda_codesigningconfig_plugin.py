from localstack.aws.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    ResourceProvider,
)


class LambdaCodeSigningConfigProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::Lambda::CodeSigningConfig"

    def __init__(self):
        self.factory: type[ResourceProvider] | None = None

    def load(self):
        from localstack.aws.services.lambda_.resource_providers.aws_lambda_codesigningconfig import (
            LambdaCodeSigningConfigProvider,
        )

        self.factory = LambdaCodeSigningConfigProvider
