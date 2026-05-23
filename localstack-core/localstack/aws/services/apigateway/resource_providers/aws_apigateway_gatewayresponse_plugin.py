from localstack.aws.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    ResourceProvider,
)


class ApiGatewayGatewayResponseProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::ApiGateway::GatewayResponse"

    def __init__(self):
        self.factory: type[ResourceProvider] | None = None

    def load(self):
        from localstack.aws.services.apigateway.resource_providers.aws_apigateway_gatewayresponse import (
            ApiGatewayGatewayResponseProvider,
        )

        self.factory = ApiGatewayGatewayResponseProvider
