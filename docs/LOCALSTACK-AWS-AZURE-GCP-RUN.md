# Guia Definitivo: LocalStack com AWS, Azure e GCP (Local & Multi-Cloud)

Como engenheiro de software e especialista em DevOps, consolidei a arquitetura e os procedimentos necessários para inicializar, configurar e testar o ecossistema multi-cloud do LocalStack (AWS, Azure e GCP) em ambiente de desenvolvimento local. 

Este guia foi elaborado a partir da análise profunda do repositório, incluindo o `AWS Server Framework (ASF)`, o novo `CloudRegistry` para multi-cloud, e os mecanismos de orquestração via Docker e Makefile.

---

## 1. Arquitetura e Inicialização (DevOps & Docker)

O LocalStack utiliza uma arquitetura baseada em plugins (gerenciada pela biblioteca `Plux`) e um Gateway de Borda (Edge Gateway) que escuta na porta `4566`. O Edge Gateway é inteligente o suficiente para identificar a nuvem destino baseado no cabeçalho `Host` ou no caminho (Path) da requisição.

### Pré-requisitos e Setup do Ambiente
Para rodar a aplicação a partir do código-fonte:

```bash
# 1. Cria o virtual environment (.venv) e instala dependências
make install

# 2. GERA OS ENTRYPOINTS (CRÍTICO!) 
# Sem isso, os provedores de serviços das nuvens não serão descobertos.
make entrypoints

# 3. Compila a imagem Docker (utiliza Docker Buildx e cache inline)
make docker-build
```

### Subindo a Infraestrutura Localmente
Não é necessário configurar variáveis de ambiente complexas para ativar o modo multi-cloud. Basta iniciar o contêiner:

```bash
# Subir via Docker Compose (recomendado para testes integrados)
docker-compose up

# OU, iniciar diretamente o runtime em Python (modo Host)
make start
# Alternativamente: localstack start
```

*Por baixo dos panos, o `bin/docker-entrypoint.sh` chama o `localstack-supervisor`, que atua como um sistema init para lidar com encerramentos graciosos e processos filhos (ex: contêineres do Lambda).*

---

## 2. AWS no LocalStack

A AWS é a implementação primária e madura do LocalStack, utilizando o **AWS Server Framework (ASF)** para espelhar chamadas RPC.

* **Implementação:** O código vive em `localstack/services/<service>/provider.py`. Os stubs da API (gerados via `botocore` e especificações Smithy) vivem em `localstack/aws/api/`. Se um serviço não estiver nativamente implementado, ele fará fallback para a biblioteca `moto`.
* **Uso Local:** Interaja utilizando o CLI `awslocal` (um wrapper para o `aws` cli apontando para localhost:4566).

### Testando Serviços AWS (Parity Testing)
A estratégia do LocalStack baseia-se em **Testes de Paridade (Snapshot Testing)**. Nós gravamos a resposta real da AWS e comparamos com o que o emulador local retorna.

1. **Gere o Snapshot na AWS Real:**
   ```bash
   DEBUG=1 TEST_DISABLE_RETRIES_AND_TIMEOUTS=1 \
   AWS_PROFILE=ls-sandbox TEST_TARGET=AWS_CLOUD \
   SNAPSHOT_UPDATE=1 pytest tests/aws/services/<service>/test_meu_servico.py
   ```
   *(Isso criará arquivos `*.snapshot.json` - **NUNCA** edite estes arquivos manualmente).*

2. **Valide contra o LocalStack:**
   Remova as variáveis da AWS para rodar o emulador localmente:
   ```bash
   pytest tests/aws/services/<service>/test_meu_servico.py
   ```

**Boas práticas de Teste:**
* Nunca use `assert` direto no corpo das respostas de API. Use sempre `snapshot.match("id", result)`.
* Adicione **Transformers** (`snapshot.add_transformer(...)`) para lidar com dados dinâmicos como ARNs e UUIDs.
* Não crie recursos soltos. Use `fixtures` que injetem em uma lista de `cleanups` (teardown) para não poluir a conta de testes.

---

## 3. Azure no LocalStack (Experimental)

O suporte à nuvem da Microsoft vive em `localstack/azure/`. Ele inclui provedores para Resource Manager, Storage (Blob/Queue/Table), Functions, Cosmos DB, entre outros.

* **Roteamento:** O Gateway do Azure intercepta requisições através do `Host` (ex: `*.blob.core.windows.net`, `login.microsoftonline.com`) ou cai para o Resource Manager caso o caminho comece com `/subscriptions/`.
* **Uso Local:** Envie requisições HTTP para a porta `4566` usando o formato de host da Azure. O LocalStack saberá interpretar automaticamente.

### Testando Serviços Azure
Os testes do Azure são altamente desacoplados em `tests/unit/azure/services/`. Eles testam a lógica Python e o roteamento HTTP:

```bash
# Rodando testes da Azure
pytest tests/unit/azure/services/
```

*Nota para Devs:* Os testes HTTP injetam instâncias falsas via `werkzeug.test.Client` e validam deserealização, códigos REST (ex: `201 Created`) e filtros OData.

---

## 4. GCP (Google Cloud) e Orquestração Multi-Cloud

A arquitetura multi-cloud moderna está definida no `CloudRegistry` (`localstack/cloud/`). O carregamento é *lazy* (preguiçoso) para manter a inicialização leve.

* **Implementação GCP:** Vive em `localstack/gcp/` e suporta serviços como Cloud Storage, Pub/Sub, Firestore e Cloud Functions.
* **Roteamento:** Funciona via DNS sniffing. Requisições apontadas para `storage.googleapis.com` ou `firestore.googleapis.com` (na porta `4566`) são enviadas para os roteadores internos da Google. O estado é separado por Projetos (`GcpProjectStore`).

### Testando Serviços GCP
A validação multi-cloud assegura que chamadas AWS, Azure e GCP podem coexistir no mesmo runtime local.

```bash
# Rodar testes do GCP
pytest tests/unit/gcp/

# Validar coexistência Multi-Cloud no Gateway de Borda
pytest tests/unit/gcp/test_multi_cloud_edge_gcp.py
```

---

## Resumo das Melhores Práticas DevOps e de Qualidade

1. **Evite `time.sleep`:** Em testes de infraestrutura e serviços (como deploy de funções ou filas), nunca pause de forma fixa. Utilize a ferramenta nativa `poll_condition`.
2. **Markers de Compatibilidade AWS:** Todo teste focado em AWS deve ser validado. Use a marcação `@markers.aws.validated`. Valide suas marcações através de `make check-aws-markers`.
3. **Format/Lint:** Antes de fazer commit em qualquer código, assegure-se de que os padrões estão aplicados:
   ```bash
   make format-modified
   make lint-modified
   ```
4. **Isolamento de Estado:** O LocalStack lida com locação multi-tenant através da injeção de contexto nas rotas (Account ID, Region e GCP Project). Nunca faça _hardcode_ de identificadores. Use sempre `account_id` e `region_name` provenientes dos fixtures do pytest.