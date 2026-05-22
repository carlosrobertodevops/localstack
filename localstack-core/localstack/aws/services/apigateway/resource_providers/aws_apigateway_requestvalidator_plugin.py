from localstack.aws.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    ResourceProvider,
)


class ApiGatewayRequestValidatorProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::ApiGateway::RequestValidator"

    def __init__(self):
        self.factory: type[ResourceProvider] | None = None

    def load(self):
        from localstack.aws.services.apigateway.resource_providers.aws_apigateway_requestvalidator import (
            ApiGatewayRequestValidatorProvider,
        )

        self.factory = ApiGatewayRequestValidatorProvider
