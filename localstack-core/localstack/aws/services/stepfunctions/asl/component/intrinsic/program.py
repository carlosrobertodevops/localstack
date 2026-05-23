from typing import Final

from localstack.aws.services.stepfunctions.asl.component.intrinsic.component import Component


class Program(Component):
    def __init__(self):
        self.statements: Final[list[Component]] = []
