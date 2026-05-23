from localstack.aws.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    ResourceProvider,
)


class StepFunctionsStateMachineProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::StepFunctions::StateMachine"

    def __init__(self):
        self.factory: type[ResourceProvider] | None = None

    def load(self):
        from localstack.aws.services.stepfunctions.resource_providers.aws_stepfunctions_statemachine import (
            StepFunctionsStateMachineProvider,
        )

        self.factory = StepFunctionsStateMachineProvider
