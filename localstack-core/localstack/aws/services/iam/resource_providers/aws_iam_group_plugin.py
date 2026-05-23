from localstack.aws.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    ResourceProvider,
)


class IAMGroupProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::IAM::Group"

    def __init__(self):
        self.factory: type[ResourceProvider] | None = None

    def load(self):
        from localstack.aws.services.iam.resource_providers.aws_iam_group import IAMGroupProvider

        self.factory = IAMGroupProvider
