from localstack.aws.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    ResourceProvider,
)


class SSMParameterProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::SSM::Parameter"

    def __init__(self):
        self.factory: type[ResourceProvider] | None = None

    def load(self):
        from localstack.aws.services.ssm.resource_providers.aws_ssm_parameter import (
            SSMParameterProvider,
        )

        self.factory = SSMParameterProvider
