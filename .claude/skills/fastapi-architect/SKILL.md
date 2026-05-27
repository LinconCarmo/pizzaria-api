---
name: fastapi-architect
description: Transforma requisitos funcionais em plano técnico detalhado para o pizzaria-api — modelo Prisma, estrutura de arquivos, endpoints, schemas Pydantic, fluxo controller→service→repository, exceções e plano de testes. Use ANTES de implementar features de média/alta complexidade, ou quando houver dúvida sobre como traduzir requisitos no padrão Layered Modular Monolith do projeto.
disable-model-invocation: true
---

# FastAPI Architect Skill

Use esta skill para transformar requisitos funcionais em um **plano técnico** aderente ao padrão Layered Modular Monolith do pizzaria-api, **sem escrever código**. A implementação é feita depois com as skills `create-module`, `create-endpoint`, `pydantic-schema`, `pytest-unit` e `pytest-integration` — este plano indica quais invocar e com quais parâmetros.

> Regras normativas: [conventions.md](../../../docs/architecture/conventions.md). Detalhe: [modular-monolith.md](../../../docs/architecture/modular-monolith.md). Decisões: ADRs (ex.: [ADR 0001](../../../docs/adr/0001-adotar-modular-monolith-em-camadas.md)). Releia sempre que houver dúvida sobre direção de dependência, fronteiras ou nomenclatura.

## Modelo mental do projeto

- **Stack**: FastAPI + Pydantic v2 + Prisma + MySQL + Redis + RabbitMQ. Python 3.13, `uv`.
- **Arquitetura**: Layered Modular Monolith ("NestJS-like" em FastAPI).
- **Estrutura por módulo** (`src/modules/<feature>/`):
  ```
  __init__.py | <entity>_router.py | controllers/v1/<entity>_controller.py | <entity>_service.py | <entity>_repository.py | <entity>_schema.py | <entity>_dependencies.py
  ```
- **Naming**: arquivos em snake_case prefixados pela entidade (`<entity>_<layer>.py`); diretório plural, prefixo singular. Regra: [conventions.md#naming](../../../docs/architecture/conventions.md#naming).
- **Versionamento de URL**: prefixo `/api/v1` aplicado em `src/main.py` no `include_router` — não no controller. Controller declara só o recurso (`prefix="/users"`). URL final = `/api/v1` + `/users` + path do handler. Exceção: `/health` sem prefixo de versão.
- **Camadas** (direção: controller → service → repository; schema transversal). Regra completa: [conventions.md#camadas](../../../docs/architecture/conventions.md#camadas).
  - **Router** (`<entity>_router.py`) — agrega `controllers/v1/<entity>_controller.py` (e futuras v2/v3). Ponto estável importado por `main.py` via `app.include_router(<feature>_router, prefix="/api/v1")`.
  - **Controller** (`controllers/v1/<entity>_controller.py`) — Pydantic in/out, chama service; sem regra/Prisma. Retorno via `-> <Response>`. OpenAPI: `summary=`, `responses=` (ver § Convenções OpenAPI).
  - **Service** (`<entity>_service.py`) — regra, orquestração, transações; lança `DomainError`, não importa Prisma. PATCH: `data.model_dump(exclude_unset=True)`.
  - **Repository** (`<entity>_repository.py`) — único que toca Prisma; Protocol + impl, retorna `dict` (nunca Pydantic). Converte `UUID` → `str` na borda; traduz erros do Prisma.
  - **Schema** (`<entity>_schema.py`) — Pydantic v2; Request e Response separados. Regra: [conventions.md#pydantic](../../../docs/architecture/conventions.md#pydantic).
- **DI**: `<entity>_dependencies.py` expõe `get_<feature>_repository` e `get_<feature>_service` com `Annotated[T, Depends(...)]`; proibido `@staticmethod`. Regra: [conventions.md#di](../../../docs/architecture/conventions.md#di).
- **Exceções de domínio**: `src/core/exceptions.py` (`DomainError` + subclasses), handlers globais em `src/main.py`. Regra: [conventions.md#erros](../../../docs/architecture/conventions.md#erros).
- **Cross-cutting**: `src/core/` (config, logger, exceptions, middlewares), `src/infra/` (database/Prisma), `src/shared/` (utils, types compartilhados).
- **Testes**: `test/unit/` (sem DB, mocks com `spec=`) e `test/integration/` (Prisma + MySQL efêmero via Testcontainers — ver template de integração).

## Convenções OpenAPI (por endpoint)

Cada endpoint no plano declara metadata Swagger: `tags` PascalCase plural, `summary` imperativo em inglês, retorno `-> <Response>`, `status_code=` explícito (201/204), e `responses=` com `ErrorResponse` cobrindo os erros esperados do verbo (`GET /{id}` → 404 · `POST` → 409 quando há unicidade · `PATCH /{id}` → 404/409 · `DELETE /{id}` → 404 · `POST /{id}/<action>` → 404/409). Regra completa: [conventions.md#openapi](../../../docs/architecture/conventions.md#openapi).

## Pre-flight: informações necessárias

Antes de elaborar o plano, reúna:

1. **Descrição funcional** — o que a feature faz do ponto de vista do usuário/negócio.
2. **Atores/permissões** (se aplicável) — quem usa, regras de autorização.
3. **Modelo de dados** — entidades, relações, atributos. Se vago, inferir e marcar como "**Suposição**".
4. **Integrações** — HTTP externo, RabbitMQ, Redis, etc.
5. **Regras de negócio** — invariantes, restrições, fluxos de estado.

Se algum input crítico está faltando, **perguntar antes de planejar**. Não inventar requisitos.

## Output: estrutura do plano

Entregar um plano em markdown com estas 9 seções:

````markdown
# Plano: <Nome da feature>

## Resumo

<2-3 frases descrevendo a feature e como ela se encaixa no projeto.>

## Modelo Prisma

<Diff/snippet do `schema.prisma`. Mostrar bloco completo com índices, uniques e FKs.
PK obrigatória: `id String @id @default(uuid()) @db.Char(36)` (ADR 0003).>

```prisma
model Order {
  id        String      @id @default(uuid()) @db.Char(36)
  status    OrderStatus @default(PENDING)
  createdAt DateTime    @default(now()) @map("created_at")

  @@map("orders")
}
```

## Estrutura de arquivos

<Árvore exata com marcação de "NOVO" / "MODIFICADO". Regra: [conventions.md#estrutura](../../../docs/architecture/conventions.md#estrutura) / [#naming](../../../docs/architecture/conventions.md#naming).>

```
src/modules/orders/                  # NOVO  (diretório plural; arquivos em snake_case prefixados por `order`)
├── __init__.py
├── order_router.py
├── controllers/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       └── order_controller.py
├── order_service.py
├── order_repository.py
├── order_schema.py
└── order_dependencies.py

src/main.py                          # MODIFICADO (include_router com prefix="/api/v1")
src/infra/prisma/schema.prisma       # MODIFICADO
```

## Endpoints

URL pública = `/api/v1` + recurso + path (ex.: `POST /api/v1/orders`).

| Método | Path (recurso) | Status | Request            | Response      | summary                | responses= | Exceções (service)           |
| ------ | -------------- | ------ | ------------------ | ------------- | ---------------------- | ---------- | ---------------------------- |
| POST   | /orders        | 201    | CreateOrderRequest | OrderResponse | Create order           | 409, 422   | ConflictError                |
| GET    | /orders/{id}   | 200    | —                  | OrderResponse | Get order by id        | 404        | NotFoundError                |
| PATCH  | /orders/{id}   | 200    | UpdateOrderRequest | OrderResponse | Update order (partial) | 404, 409   | NotFoundError, ConflictError |
| DELETE | /orders/{id}   | 204    | —                  | —             | Soft delete order      | 404        | NotFoundError                |

## Schemas Pydantic

<Assinatura dos DTOs — nomes, campos, tipos, validações chave. A skill `pydantic-schema` gera o código completo.>

- `CreateOrderRequest { customer_id: UUID, items: list[OrderItemRequest] }`
- `OrderResponse { id: UUID, status: OrderStatus, created_at: datetime }`

## Fluxo de execução

<Sequência por endpoint, camada a camada.>

### POST /api/v1/orders

1. Controller (`controllers/v1/order_controller.py`) recebe `CreateOrderRequest`; injeta `Annotated[OrderService, Depends(get_order_service)]`.
2. Service `OrderService.create`:
   1. Valida existência do customer (chama `customer_repository.find_by_id`).
   2. Persiste order via repository.
3. Repository persiste via Prisma; `UniqueViolationError` → `ConflictError`.
4. Controller retorna `OrderResponse`.

### PATCH /api/v1/orders/{order_id}

1. Controller recebe `UpdateOrderRequest`.
2. Service `OrderService.update`: `payload = data.model_dump(exclude_unset=True)` — só campos enviados.
3. Repository `update` com campos parciais; `RecordNotFoundError` → `NotFoundError`.
4. Controller retorna `OrderResponse`.

## Dependências entre módulos

<Imports cross-module sempre via Protocol importado do módulo dono.>

- `OrderService` usa `CustomerRepositoryProtocol` de `src/modules/customers/customer_repository.py` (import: `from src.modules.customers.customer_repository import CustomerRepositoryProtocol`).

## Exceções

<Quais exceções o service lança e em que condições. Se precisar de exceção nova, propor a definição.>

- `NotFoundError("Customer {id} not found")` — quando customer não existe.
- `ConflictError("Order already finalized")` — transição de status inválida.

## Plano de testes

> Regra geral de testes e factories (AAA, `spec=`, sem `Any`, as 4 variantes de factory, cobertura mínima): [conventions.md#testes](../../../docs/architecture/conventions.md#testes). Abaixo, o que o plano deve listar especificamente para esta feature.

### Factories (`test/factories/<entity>_factory.py`)

- `make_<entity>_row`, `make_<entity>_response`, `make_create_<entity>_request`, `seed_<entity>` — com os campos/overrides específicos da entidade desta feature.

### Unit (`test/unit/modules/<feature>/`)

- `test_<entity>_service.py`: happy path + erros principais (404, 409, 422).
- `test_<entity>_schema.py`: validações de campo (formato, limites).

### Integration (`test/integration/modules/<feature>/`)

- Infra: **Testcontainers** (`MySqlContainer`) — `conftest.py` sobe container efêmero, aplica migrations e expõe `db`, `client` (`httpx.AsyncClient`), `clean_database` (autouse). `pytestmark = pytest.mark.integration`.
- `test_<entity>_controller.py`: pipeline HTTP completo contra `/api/v1/<feature>/...`.
  - ≥ 1 happy path por endpoint (assert HTTP + estado no DB) e ≥ 1 erro esperado (404 / 409 / 422).
  - Payloads via `make_create_<entity>_request(...).model_dump(mode="json")`; contexto pré-existente via `seed_<entity>`.

## Implementação — skills a invocar (em ordem)

1. **(manual)** Editar `src/infra/prisma/schema.prisma` com os models propostos.
2. **(manual)** `poe prisma-migrate-create` — gera migration e roda.
3. **Skill `create-module <feature>`** — scaffold inicial (inclui `test/factories/<entity>_factory.py`).
4. **Skill `pydantic-schema`** — preencher schemas conforme tabela acima.
5. **Skill `create-endpoint`** — para cada endpoint além do CRUD básico.
6. **Skill `pytest-unit`** + **Skill `pytest-integration`** — testes com factories de `test/factories/<entity>_factory.py`.

## Suposições / pontos a confirmar

<Lista explícita de tudo que foi assumido por falta de informação.>

- **Suposição**: ...
````

## Diretrizes operacionais

**Fazer:**

- Ler `src/`, `schema.prisma` e `src/core/exceptions.py` para entender o estado atual.
- Buscar features similares já implementadas para reuso de padrões.
- Marcar trade-offs explicitamente (ex: "denormalizar campo X — aceita custo de consistência eventual").
- Identificar quando uma feature deve ser dividida em múltiplos módulos (1 bounded context = 1 módulo).
- Sugerir exceções novas em `src/core/exceptions.py` quando as existentes não cobrem.
- Indicar quando o caso pede transação Prisma multi-write.
- Listar todas as suposições explicitamente.

**Não fazer:**

- Escrever código de produção. A saída é o plano markdown.
- Rodar comandos que mudam state (`prisma migrate`, edits). Sugerir no plano — execução é do implementador.
- Tomar decisões irreversíveis sem sinalizar (schema do banco, breaking changes de API).
- Inventar requisitos. Se ambíguo, listar como suposição ou perguntar.
- Duplicar conteúdo das skills. Referenciar `create-module`, `create-endpoint`, etc. — não reescrever templates.

## Heurísticas para decisões comuns

| Pergunta                           | Heurística                                                                                                                                          |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Módulo único ou múltiplos?         | 1 bounded context (linguagem ubíqua coerente) = 1 módulo. Se o time falaria "User" e "Profile" como coisas separadas, são 2 módulos.                |
| Campo no model ou tabela à parte?  | Dado faz parte da identidade do recurso? Embed. É um tipo aberto (eventos, versões, histórico)? Tabela à parte.                                     |
| Onde vai a regra?                  | Validação de formato → schema (Pydantic). Validação que envolve DB (existência, unicidade) → service.                                               |
| Síncrono ou assíncrono (RabbitMQ)? | Operação precisa ser observável imediatamente no response? Síncrono. Pode ser "fire and forget" / cross-service? Assíncrono.                        |
| Cache (Redis)?                     | Read-heavy + dado muda <10x/dia + tolera staleness curta? Cachear. Caso contrário, não.                                                             |
| Soft delete?                       | Recurso tem auditoria/histórico relevante (usuários, transações)? Soft delete (`deleted_at`). Recurso descartável (sessão, cache row)? Hard delete. |

## Auto-check antes de entregar o plano

- [ ] Plano cobre as 9 seções da estrutura acima.
- [ ] Estrutura de arquivos lista NOVO/MODIFICADO explicitamente.
- [ ] Cada endpoint tem método + path + status + Request + Response + exceções.
- [ ] Fluxo de execução está descrito camada a camada.
- [ ] Dependências cross-module listadas com referência ao Protocol.
- [ ] Factories esperadas em `test/factories/<entity>_factory.py` listadas (`make_<entity>_row`, `make_<entity>_response`, `make_create_<entity>_request`, `seed_<entity>`).
- [ ] Plano de testes cobre happy + erros principais (unit + integration com Testcontainers).
- [ ] Endpoints com 4xx esperado documentam `responses=` com `ErrorResponse` e `summary` em inglês.
- [ ] Fluxos PATCH descrevem `model_dump(exclude_unset=True)` no service.
- [ ] `main.py` registra router com `prefix="/api/v1"` (exceto health).
- [ ] Suposições marcadas explicitamente.
- [ ] Sequência de skills a invocar é clara.
