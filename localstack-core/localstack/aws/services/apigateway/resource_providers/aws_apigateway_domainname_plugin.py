from localstack.aws.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    ResourceProvider,
)


class ApiGatewayDomainNameProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::ApiGateway::DomainName"

    def __init__(self):
        self.factory: type[ResourceProvider] | None = None

    def load(self):
        from localstack.aws.services.apigateway.resource_providers.aws_apigateway_domainname import (
            ApiGatewayDomainNameProvider,
        )

        self.factory = ApiGatewayDomainNameProvider
