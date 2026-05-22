from localstack.aws.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    ResourceProvider,
)


class SecretsManagerResourcePolicyProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::SecretsManager::ResourcePolicy"

    def __init__(self):
        self.factory: type[ResourceProvider] | None = None

    def load(self):
        from localstack.aws.services.secretsmanager.resource_providers.aws_secretsmanager_resourcepolicy import (
            SecretsManagerResourcePolicyProvider,
        )

        self.factory = SecretsManagerResourcePolicyProvider
