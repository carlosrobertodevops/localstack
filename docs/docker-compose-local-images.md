# Docker Compose sem token e com imagem local

Este guia resume como subir o LocalStack via Docker Compose sem `LOCALSTACK_AUTH_TOKEN` e como usar uma imagem Docker própria.

## Compose Community

Use `docker-compose.yml` quando não houver token Pro:

```bash
docker compose -f docker-compose.yml up
```

Esse compose usa a imagem Community por padrão:

```yaml
image: ${LOCALSTACK_IMAGE:-localstack/localstack}
```

Sem `LOCALSTACK_AUTH_TOKEN`, apenas recursos Community/Core ficam disponíveis.

## Compose Pro

Use `docker-compose-pro.yml` apenas com token:

```bash
LOCALSTACK_AUTH_TOKEN=... docker compose -f docker-compose-pro.yml up
```

O token é obrigatório neste arquivo:

```yaml
LOCALSTACK_AUTH_TOKEN=${LOCALSTACK_AUTH_TOKEN:?}
```

Sem token, o Compose falha antes de criar o container.

## Imagem Docker própria

Para buildar uma imagem local do projeto:

```bash
make install
make entrypoints
IMAGE_NAME=localstack/localstack-custom DEFAULT_TAG=dev IMAGE_TAG=dev make docker-build
```

Para subir usando essa imagem no compose Community:

```bash
LOCALSTACK_IMAGE=localstack/localstack-custom:dev docker compose -f docker-compose.yml up
```

Para uma imagem Pro própria, mantenha o token e use `LOCALSTACK_PRO_IMAGE`:

```bash
LOCALSTACK_AUTH_TOKEN=... LOCALSTACK_PRO_IMAGE=sua-imagem-pro:dev docker compose -f docker-compose-pro.yml up
```

## Limitações

- Imagem Community própria não habilita recursos Pro.
- `LOCALSTACK_AUTH_TOKEN` não transforma `localstack/localstack` em Pro.
- Recursos Pro exigem imagem/código Pro e token válido.
- O Docker socket é montado em `/var/run/docker.sock`; use apenas em ambiente local confiável.
- Tags como `latest` são mutáveis; prefira tags explícitas para reprodutibilidade.

## Validação rápida

Renderizar compose Community:

```bash
docker compose -f docker-compose.yml config --quiet
```

Validar imagem custom no Community:

```bash
LOCALSTACK_IMAGE=localstack/localstack-custom:dev docker compose -f docker-compose.yml config
```

Validar que Pro exige token:

```bash
env -u LOCALSTACK_AUTH_TOKEN docker compose -f docker-compose-pro.yml config --quiet
```

O resultado esperado é erro informando que `LOCALSTACK_AUTH_TOKEN` está ausente.
