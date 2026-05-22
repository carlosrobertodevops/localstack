from __future__ import annotations

from abc import ABC

from localstack.aws.services.stepfunctions.asl.component.eval_component import EvalComponent


class Comparison(EvalComponent, ABC): ...
