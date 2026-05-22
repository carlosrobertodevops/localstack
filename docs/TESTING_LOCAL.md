# Testing LocalStack Locally — Passo a Passo

Guia mínimo para rodar testes e o container LocalStack em uma máquina dev.

## 0. Pré-requisitos

- Python **3.13+** (o código usa `from warnings import deprecated` (PEP 702, 3.13+) e `class Foo[T]` (PEP 695, 3.12+); o `pyproject.toml` declara `>=3.10`, mas o código real exige 3.13).
- Docker rodando (`docker info` deve responder).
- Make, git.
- (Opcional) `awslocal` CLI: `pip install awscli-local`.

## 1. Ambiente Python

Escolha **um** dos caminhos.

### 1a. Make + venv (caminho oficial)

```bash
cd /Users/carlosroberto/Workspace/Projetos/localstack
make install            # cria .venv/ e instala dev extras
source .venv/bin/activate
python -m plux entrypoints   # regenera plux.ini se mexer em plugins
```

### 1b. Conda (alternativa)

```bash
source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh
conda create -n localstack python=3.13 -y
conda activate localstack
cd /Users/carlosroberto/Workspace/Projetos/localstack
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[test]" 'cbor2<6'   # cbor2 6.x removeu cbor2._decoder
python -m plux entrypoints
```

> **Por que `python -m pytest` e não `pytest`?**
> `~/.local/bin/pytest` (pipx/user install) pode ter precedência no `$PATH` e usar o Python errado, causando `ModuleNotFoundError: No module named 'localstack'`. Sempre invoque via `python -m pytest` dentro do env ativo.

## 2. Sanidade do ambiente

```bash
python -c "import localstack, sys; print(sys.executable); print('plux:', __import__('plux').__version__)"
python -m pytest --collect-only tests/unit/test_tagging.py | tail -5
```

Deve listar testes coletados sem `ImportError`.

## 3. Rodar testes

### Unit

```bash
python -m pytest tests/unit/                       # tudo
python -m pytest tests/unit/test_tagging.py        # um arquivo
python -m pytest tests/unit/test_tagging.py -k test_get_tags  # um teste
python -m pytest -x -vv tests/unit/test_tagging.py # parar no 1º fail, verboso
```

### Integração / parity (precisa Docker)

```bash
python -m pytest tests/aws/services/s3/                       # um serviço
python -m pytest tests/aws/ -m "not aws_validated"            # só os mockáveis
```

### Parity contra AWS real (snapshots)

Refresca snapshots batendo na AWS real:

```bash
AWS_PROFILE=<seu-perfil> TEST_TARGET=AWS_CLOUD SNAPSHOT_UPDATE=1 \
  python -m pytest tests/aws/services/s3/test_s3.py -k test_put_get
```

Sem `SNAPSHOT_UPDATE=1` o teste **valida** snapshot atual contra AWS real.

### Bootstrap (container)

```bash
python -m pytest tests/bootstrap/
```

### Via Make

```bash
make test TEST_PATH=tests/unit/test_tagging.py
make check-aws-markers         # verifica markers em tests/aws/
```

### Suite dentro do container (`make docker-run-tests`)

⚠️ A imagem pública `localstack/localstack:latest` é **stripped** (só `.venv` + `requirements-runtime.txt`, sem Makefile/source). O target falha com `No rule to make target 'install-test'`. Workflow correto:

```bash
# Pré-requisito: setuptools_scm no python do PATH (bin/docker-helper.sh exige)
python3 -m pip install setuptools_scm   # ou: pip install no venv/conda env ativo

docker rmi localstack/localstack:latest 2>/dev/null || true
make docker-build              # rebuilda local (Dockerfile copia Makefile + localstack-core/)
make docker-run-tests          # agora encontra install-test no Makefile interno
```

Se `python3` do PATH for externamente-gerenciado (Homebrew/PEP 668), prependa o env:

```bash
PATH=/Users/carlosroberto/.conda/envs/localstack/bin:$PATH make docker-build
```

Para evitar sobrescrever a imagem pública use tag custom:

```bash
IMAGE_NAME=localstack/localstack-dev make docker-build
IMAGE_NAME=localstack/localstack-dev DEFAULT_TAG=latest make docker-run-tests
```

## 4. Lint / format antes de commitar

```bash
make lint-modified
make format-modified
```

## 5. Subir o container LocalStack

### Opção A — CLI (gerencia container)

```bash
pip install localstack
localstack start -d         # background
localstack status services  # quais serviços responderam
localstack logs             # tail
localstack stop
```

### Opção B — docker compose (deste repo)

```bash
docker-compose up            # foreground
# em outro terminal:
curl http://localhost:4566/_localstack/health | jq
docker-compose down
```

### Opção C — imagem custom build (testar mudanças)

```bash
docker build -t localstack/localstack:dev .
DOCKER_IMAGE_NAME=localstack/localstack:dev localstack start -d
```

## 6. Smoke test rápido (S3 + SQS)

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

aws s3 mb s3://demo-bucket
echo "hello" | aws s3 cp - s3://demo-bucket/hello.txt
aws s3 ls s3://demo-bucket/

aws sqs create-queue --queue-name demo-queue
aws sqs send-message --queue-url http://localhost:4566/000000000000/demo-queue --message-body "hi"
aws sqs receive-message --queue-url http://localhost:4566/000000000000/demo-queue
```

Com `awslocal`:

```bash
awslocal s3 mb s3://demo
awslocal sqs list-queues
```

## 7. Debug / iteração

| Cenário                                               | Comando                                              |
| ----------------------------------------------------- | ---------------------------------------------------- |
| Editar código + rerodar (editable install já reflete) | `python -m pytest <path>`                            |
| Logs verbose do container                             | `LS_LOG=trace localstack start`                      |
| Inspecionar estado interno                            | `curl localhost:4566/_localstack/diagnose`           |
| Listar plugins carregados                             | `python -m plux show`                                |
| Regenerar entrypoints após novo plugin                | `python -m plux entrypoints` (ou `make entrypoints`) |
| Limpar tudo                                           | `make clean`                                         |

## 8. Troubleshooting

| Erro                                                           | Causa                               | Fix                                               |
| -------------------------------------------------------------- | ----------------------------------- | ------------------------------------------------- |
| `ModuleNotFoundError: No module named 'localstack'`            | pytest do PATH ≠ env ativo          | use `python -m pytest`, ative venv/conda          |
| `SyntaxError: class Foo[T]`                                    | Python < 3.12 (PEP 695)             | recrie env com 3.13                               |
| `ImportError: cannot import name 'deprecated' from 'warnings'` | Python < 3.13 (PEP 702)             | recrie env com 3.13                               |
| `ImportError: No module named 'cbor2._decoder'`                | cbor2 6.x removeu submódulo interno | `pip install 'cbor2<6'`                           |
| `Refusing upload, dist does not contain entrypoints`           | `plux.ini` vazio                    | `make entrypoints`                                |
| Docker socket permission                                       | macOS rosetta / docker desktop off  | reinicie Docker Desktop                           |
| `port 4566 already in use`                                     | container anterior vivo             | `localstack stop` ou `docker ps` + `docker rm -f` |

## 9. Referências

- `CLAUDE.md` — visão arquitetural e comandos chave.
- `AGENTS.md` — convenções de teste / parity / snapshots.
- `docs/testing/` — docs oficiais de teste.
- `localstack-core/localstack/testing/pytest/fixtures.py` — fixtures comuns.
