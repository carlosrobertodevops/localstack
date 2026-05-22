from typing import Final

from localstack.aws.services.stepfunctions.asl.component.component import Component
from localstack.aws.services.stepfunctions.asl.component.state.state_choice.choice_rule import (
    ChoiceRule,
)


class ChoicesDecl(Component):
    def __init__(self, rules: list[ChoiceRule]):
        self.rules: Final[list[ChoiceRule]] = rules
