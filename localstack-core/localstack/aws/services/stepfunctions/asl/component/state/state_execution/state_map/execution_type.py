from enum import Enum

from localstack.aws.services.stepfunctions.asl.antlr.runtime.ASLLexer import ASLLexer


class ExecutionType(Enum):
    Standard = ASLLexer.STANDARD
