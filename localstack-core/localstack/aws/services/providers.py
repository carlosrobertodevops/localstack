from localstack.aws.forwarder import HttpFallbackDispatcher
from localstack.aws.services.plugins import (
    Service,
    aws_provider,
)


@aws_provider()
def acm():
    from localstack.aws.services.acm.provider import AcmProvider
    from localstack.aws.services.moto import MotoFallbackDispatcher

    provider = AcmProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def apigateway():
    from localstack.aws.services.apigateway.next_gen.provider import ApigatewayNextGenProvider
    from localstack.aws.services.moto import MotoFallbackDispatcher

    provider = ApigatewayNextGenProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="apigateway", name="next_gen")
def apigateway_next_gen():
    from localstack.aws.services.apigateway.next_gen.provider import ApigatewayNextGenProvider
    from localstack.aws.services.moto import MotoFallbackDispatcher

    provider = ApigatewayNextGenProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="apigateway", name="legacy")
def apigateway_legacy():
    from localstack.aws.services.apigateway.legacy.provider import ApigatewayProvider
    from localstack.aws.services.moto import MotoFallbackDispatcher

    provider = ApigatewayProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="cloudformation", name="engine-legacy")
def cloudformation():
    from localstack.aws.services.cloudformation.provider import CloudformationProvider

    provider = CloudformationProvider()
    return Service.for_provider(provider)


@aws_provider(api="cloudformation")
def cloudformation_v2():
    from localstack.aws.services.cloudformation.v2.provider import CloudformationProviderV2

    provider = CloudformationProviderV2()
    return Service.for_provider(provider)


@aws_provider(api="config")
def awsconfig():
    from localstack.aws.services.configservice.provider import ConfigProvider
    from localstack.aws.services.moto import MotoFallbackDispatcher

    provider = ConfigProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="cloudwatch", name="default")
def cloudwatch():
    from localstack.aws.services.cloudwatch.provider_v2 import CloudwatchProvider

    provider = CloudwatchProvider()
    return Service.for_provider(provider)


@aws_provider(api="cloudwatch", name="v1")
def cloudwatch_v1():
    from localstack.aws.services.cloudwatch.provider import CloudwatchProvider
    from localstack.aws.services.moto import MotoFallbackDispatcher

    provider = CloudwatchProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="cloudwatch", name="v2")
def cloudwatch_v2():
    from localstack.aws.services.cloudwatch.provider_v2 import CloudwatchProvider

    provider = CloudwatchProvider()
    return Service.for_provider(provider)


@aws_provider()
def dynamodb():
    from localstack.aws.services.dynamodb.provider import DynamoDBProvider

    provider = DynamoDBProvider()
    return Service.for_provider(
        provider,
        dispatch_table_factory=lambda _provider: HttpFallbackDispatcher(
            _provider, _provider.get_forward_url
        ),
    )


@aws_provider(api="dynamodbstreams", name="v2")
def dynamodbstreams_v2():
    from localstack.aws.services.dynamodbstreams.v2.provider import DynamoDBStreamsProvider

    provider = DynamoDBStreamsProvider()
    return Service.for_provider(provider)


@aws_provider(api="dynamodb", name="v2")
def dynamodb_v2():
    from localstack.aws.services.dynamodb.v2.provider import DynamoDBProvider

    provider = DynamoDBProvider()
    return Service.for_provider(
        provider,
        dispatch_table_factory=lambda _provider: HttpFallbackDispatcher(
            _provider, _provider.get_forward_url
        ),
    )


@aws_provider()
def dynamodbstreams():
    from localstack.aws.services.dynamodbstreams.provider import DynamoDBStreamsProvider

    provider = DynamoDBStreamsProvider()
    return Service.for_provider(provider)


@aws_provider()
def ec2():
    from localstack.aws.services.ec2.provider import Ec2Provider
    from localstack.aws.services.moto import MotoFallbackDispatcher

    provider = Ec2Provider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def es():
    from localstack.aws.services.es.provider import EsProvider

    provider = EsProvider()
    return Service.for_provider(provider)


@aws_provider()
def firehose():
    from localstack.aws.services.firehose.provider import FirehoseProvider

    provider = FirehoseProvider()
    return Service.for_provider(provider)


@aws_provider()
def iam():
    from localstack.aws.services.iam.provider import IamProvider
    from localstack.aws.services.moto import MotoFallbackDispatcher

    provider = IamProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def sts():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.sts.provider import StsProvider

    provider = StsProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def kinesis():
    from localstack.aws.services.kinesis.provider import KinesisProvider

    provider = KinesisProvider()
    return Service.for_provider(
        provider,
        dispatch_table_factory=lambda _provider: HttpFallbackDispatcher(
            _provider, _provider.get_forward_url
        ),
    )


@aws_provider()
def kms():
    from localstack.aws.services.kms.provider import KmsProvider

    provider = KmsProvider()
    return Service.for_provider(provider)


@aws_provider(api="lambda")
def lambda_():
    from localstack.aws.services.lambda_.provider import LambdaProvider

    provider = LambdaProvider()
    return Service.for_provider(provider)


@aws_provider(api="lambda", name="asf")
def lambda_asf():
    from localstack.aws.services.lambda_.provider import LambdaProvider

    provider = LambdaProvider()
    return Service.for_provider(provider)


@aws_provider(api="lambda", name="v2")
def lambda_v2():
    from localstack.aws.services.lambda_.provider import LambdaProvider

    provider = LambdaProvider()
    return Service.for_provider(provider)


@aws_provider()
def logs():
    from localstack.aws.services.logs.provider import LogsProvider
    from localstack.aws.services.moto import MotoFallbackDispatcher

    provider = LogsProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def opensearch():
    from localstack.aws.services.opensearch.provider import OpensearchProvider

    provider = OpensearchProvider()
    return Service.for_provider(provider)


@aws_provider()
def redshift():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.redshift.provider import RedshiftProvider

    provider = RedshiftProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def route53():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.route53.provider import Route53Provider

    provider = Route53Provider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def route53resolver():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.route53resolver.provider import Route53ResolverProvider

    provider = Route53ResolverProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def s3():
    from localstack.aws.services.s3.provider import S3Provider

    provider = S3Provider()
    return Service.for_provider(provider)


@aws_provider()
def s3control():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.s3control.provider import S3ControlProvider

    provider = S3ControlProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def scheduler():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.scheduler.provider import SchedulerProvider

    provider = SchedulerProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def secretsmanager():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.secretsmanager.provider import SecretsmanagerProvider

    provider = SecretsmanagerProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def ses():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.ses.provider import SesProvider

    provider = SesProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def sns():
    from localstack.aws.services.sns.provider import SnsProvider

    provider = SnsProvider()
    return Service.for_provider(provider)


@aws_provider()
def sqs():
    from localstack.aws.services.sqs.provider import SqsProvider

    provider = SqsProvider()
    return Service.for_provider(provider)


@aws_provider()
def ssm():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.ssm.provider import SsmProvider

    provider = SsmProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="events", name="default")
def events():
    from localstack.aws.services.events.provider import EventsProvider

    provider = EventsProvider()
    return Service.for_provider(provider)


@aws_provider(api="events", name="v2")
def events_v2():
    from localstack.aws.services.events.provider import EventsProvider

    provider = EventsProvider()
    return Service.for_provider(provider)


@aws_provider(api="events", name="v1")
def events_v1():
    from localstack.aws.services.events.v1.provider import EventsProvider
    from localstack.aws.services.moto import MotoFallbackDispatcher

    provider = EventsProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="events", name="legacy")
def events_legacy():
    from localstack.aws.services.events.v1.provider import EventsProvider
    from localstack.aws.services.moto import MotoFallbackDispatcher

    provider = EventsProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def stepfunctions():
    from localstack.aws.services.stepfunctions.provider import StepFunctionsProvider

    provider = StepFunctionsProvider()
    return Service.for_provider(provider)


# TODO: remove with 4.1.0 to allow smooth deprecation path for users that have v2 set manually
@aws_provider(api="stepfunctions", name="v2")
def stepfunctions_v2():
    # provider for people still manually using `v2`
    from localstack.aws.services.stepfunctions.provider import StepFunctionsProvider

    provider = StepFunctionsProvider()
    return Service.for_provider(provider)


@aws_provider()
def swf():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.swf.provider import SWFProvider

    provider = SWFProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def resourcegroupstaggingapi():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.resourcegroupstaggingapi.provider import (
        ResourcegroupstaggingapiProvider,
    )

    provider = ResourcegroupstaggingapiProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider(api="resource-groups")
def resource_groups():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.resource_groups.provider import ResourceGroupsProvider

    provider = ResourceGroupsProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def support():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.support.provider import SupportProvider

    provider = SupportProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)


@aws_provider()
def transcribe():
    from localstack.aws.services.moto import MotoFallbackDispatcher
    from localstack.aws.services.transcribe.provider import TranscribeProvider

    provider = TranscribeProvider()
    return Service.for_provider(provider, dispatch_table_factory=MotoFallbackDispatcher)
