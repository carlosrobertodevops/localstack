from enum import Enum

from localstack.aws.services.stepfunctions.asl.antlr.runtime.ASLLexer import ASLLexer


class Mode(Enum):
    Inline = ASLLexer.INLINE
    Distributed = ASLLexer.DISTRIBUTED
