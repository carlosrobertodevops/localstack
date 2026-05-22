from localstack.aws.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    ResourceProvider,
)


class LambdaLayerVersionProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::Lambda::LayerVersion"

    def __init__(self):
        self.factory: type[ResourceProvider] | None = None

    def load(self):
        from localstack.aws.services.lambda_.resource_providers.aws_lambda_layerversion import (
            LambdaLayerVersionProvider,
        )

        self.factory = LambdaLayerVersionProvider
