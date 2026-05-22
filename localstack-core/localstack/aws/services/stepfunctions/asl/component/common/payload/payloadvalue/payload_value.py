import abc

from localstack.aws.services.stepfunctions.asl.component.eval_component import EvalComponent


class PayloadValue(EvalComponent, abc.ABC): ...
