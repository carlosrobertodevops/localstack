# Análise

## Usei CodeGraph, graphify existente e 3 subagentes. Não editei arquivos. Não rodei suíte.

## Projeto é Python grande do LocalStack:

- Core: localstack-core/localstack/
- Serviços AWS: localstack-core/localstack/services/<service>/
- Testes: tests/unit, tests/integration, tests/aws, tests/bootstrap, tests/performance
- Padrão serviço: provider.py, models.py, resource_providers/
- API gerada: localstack-core/localstack/aws/api/\*, não editar
  Pontos Centrais
  Graphify mostra hubs fortes:
- short_uid() usado transversalmente.
- ResourceProvider, ProgressEvent, ResourceRequest, OperationStatus são núcleo CloudFormation.
- Fixtures como deploy_cfn_template(), sqs_create_queue(), aws_client_factory() são arquitetura de teste real.
- S3/SQS/SNS/Lambda têm suítes grandes e centrais.
- StepFunctions tem grafo interno denso: parser/preprocessor/environment.

## Como Testar

### Instalar deps de teste:

```bash
make install-test
# Rodar teste unitário específico:
pytest tests/unit/test_tagging.py
# Rodar arquivo específico:
pytest tests/aws/services/s3/test_s3.py
# Rodar teste por nome:
pytest tests/aws/services/s3/test_s3.py -k test_nome
# Via Makefile:
TEST_PATH="tests/unit/test_tagging.py" make test
# Com logs:
PYTEST_LOGLEVEL=INFO TEST_PATH="tests/aws/services/s3/test_s3.py" make test
# Testes AWS/localstack sem iniciar instância nova:
TEST_SKIP_LOCALSTACK_START=1 pytest tests/aws/services/s3/test_s3.py
# Verificar markers AWS:
make check-aws-markers
# Paridade AWS
# Contra AWS real:
AWS_PROFILE=ls-sandbox TEST_TARGET=AWS_CLOUD pytest tests/aws/services/s3/test_s3.py
# Atualizar snapshot contra AWS:
AWS_PROFILE=ls-sandbox TEST_TARGET=AWS_CLOUD SNAPSHOT_UPDATE=1 pytest tests/aws/services/s3/test_s3.py
# Depois rode local sem TEST_TARGET=AWS_CLOUD.
```

## Regras Críticas

- Não editar _.snapshot.json nem _.validation.json manualmente.
- Teste validado AWS usa snapshot.match(), não assert puro.
- Criar recursos via fixtures, não direto no corpo do teste.
- Não hardcodar conta/região; usar account_id, region_name.
- Não editar localstack-core/localstack/aws/api/\*.
  Estratégia Prática
- Mudou provider.py: rode teste do serviço em tests/aws/services/<service>/.
- Mudou models.py: rode unit + teste AWS do serviço.
- Mudou CloudFormation/resource provider: rode testes de tests/aws/services/cloudformation/....
- Mudou fixture comum: rode arquivo inteiro dos serviços afetados, não só -k.
- Mudou StepFunctions parser: rode regressões ASL/cenários, não só unit pequeno.
