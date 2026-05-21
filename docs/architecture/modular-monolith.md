# Modular Monolith em Camadas — Guideline Arquitetural

Este documento descreve **como** organizar o código do `pizzaria-api`. É um guia vivo que reflete o padrão atual em uso. A **decisão** de adotar este padrão está registrada em `[docs/adr/0001-adotar-modular-monolith-em-camadas.md](../adr/0001-adotar-modular-monolith-em-camadas.md)`.

> Para scaffold automatizado deste padrão, use as skills `create-module`, `create-endpoint`, `pydantic-schema`, `pytest-unit` e `pytest-integration`. Para planejamento e revisão, use os agents `fastapi-architect` e `pizzaria-reviewer`.

---

## 1. Stack

- **Python 3.13** + **uv** (gerenciador de pacotes/lockfile).
- **FastAPI** como framework web.
- **Pydantic v2** para DTOs (Request/Response).
- **Prisma** (Python) como ORM, conectado a **MySQL**.
- **Redis** (cache) e **RabbitMQ** (mensageria), quando aplicável.
- **Loguru** para logging estruturado.

---

## 2. Estrutura de diretórios

```
src/
├── main.py                    # bootstrap FastAPI + registro de routers/handlers
├── app.module.py              # composição de dependências de nível raiz
├── core/                      # cross-cutting concerns
│   ├── config.py              # settings (env vars)
│   ├── logger.py              # configuração loguru
│   ├── exceptions.py          # DomainError + subclasses + status mapping
│   ├── middlewares.py         # middlewares globais
│   └── security.py            # auth/JWT/hashing
├── infra/                     # adapters de infraestrutura
│   ├── database.py            # instância singleton do client Prisma
│   └── prisma/                # schema.prisma + migrations
├── shared/                    # utilidades genuinamente transversais
│   ├── types.py               # tipos compartilhados (BaseSchema, etc.)
│   ├── decorators.py
│   └── utills.py
└── modules/                   # features (bounded contexts)
    ├── health/
    └── users/
```

### Princípio: `shared/` é minimalista

`src/shared/` é uma armadilha — vira lixeira rapidamente. Coloque ali **apenas** o que é genuinamente transversal e estável: tipos como `BaseSchema`, decoradores, helpers que vários módulos realmente compartilham. Na dúvida, **duplique** entre módulos. Duplicação é mais barata que acoplamento errado.

---

## 3. Estrutura interna de um módulo

Cada feature vive em `src/modules/<feature>/` com **7 arquivos** em layout flat (sem subpastas):

```
src/modules/<feature>/
├── __init__.py        # vazio (marker de package)
├── router.py          # APIRouter — prefix, tags, agrega controllers
├── controller.py      # handlers HTTP — recebe Pydantic, chama service
├── service.py         # regra de negócio — lança DomainError
├── repository.py      # acesso a Prisma — Protocol + implementação
├── schema.py          # DTOs Pydantic v2 — *Request / *Response
└── dependencies.py    # FastAPI Depends() — wiring repository → service
```

### Naming

- **Arquivos curtos, sem prefixo do módulo.** O diretório já dá contexto.
  - ✅ `src/modules/orders/controller.py`
  - ❌ `src/modules/orders/orders.controller.py`
  - ❌ `src/modules/orders/orders_controller.py`
- **Módulo em snake_case**, plural para recursos (`orders`, `products`), singular para conceitos (`auth`, `billing`).

> **Histórico**: `src/modules/users/` usava o estilo NestJS (`users.module.py`, `users.repository.py`). Migrado para o padrão flat na rodada de aderência (2026-05-20). Não reintroduzir.

---

## 4. Camadas e responsabilidades

Direção de dependência: **controller → service → repository**. Schema é transversal (importado por todas).

### Controller (`controller.py`)

- Recebe DTO Pydantic, chama o service, retorna DTO Pydantic.
- **Sem regra de negócio.** Sem cálculos, sem ifs de fluxo, sem validações cruzadas.
- **Sem `try/except`** — handlers globais em [src/main.py](../../src/main.py) cuidam de `DomainError`, `RequestValidationError` e `Exception`.
- **Sem `HTTPException`** — quem sinaliza erro é o service via `DomainError`.
- **Sem import de Prisma.** Controller só conhece o service.
- **Anotação de retorno**: usar `-> <Response>` como anotação do handler em vez de `response_model=` no decorator. FastAPI gera a mesma OpenAPI a partir do return type, e a anotação fica em um lugar só.
- `status_code=status.HTTP_*` no decorator quando não for 200.
- **DI com `Annotated`** (recomendado FastAPI ≥ 0.95): `service: Annotated[XService, Depends(get_x_service)]` — evita o default mutável e satisfaz linters como SonarLint/python:S8410.

### Service (`service.py`)

- Orquestra repositories, aplica regra de negócio, monta DTOs de saída.
- **Nunca importa Prisma.** Depende do `<X>RepositoryProtocol`, não da classe concreta.
- Lança `DomainError` (ou subclasses) — `NotFoundError`, `ConflictError`, `ValidationError`, `UnauthorizedError`.
- **Sem `@staticmethod`** — service é instanciado via DI e recebe colaboradores no `__init__`.
- Para PATCH, usa `data.model_dump(exclude_unset=True)` para não sobrescrever campos não enviados.

### Repository (`repository.py`)

- **Único arquivo do módulo que importa Prisma.**
- Define um `<X>RepositoryProtocol` (interface) e a classe concreta `<X>Repository` que recebe `db: Prisma` no construtor.
- Métodos retornam `dict` ou `dict | None` (resultado bruto do Prisma) — conversão para Pydantic é responsabilidade do service.
- I/O puro. Sem regra de negócio (cálculo de total, checagem de status, etc.).

### Schema (`schema.py`)

- DTOs Pydantic v2.
- **Request e Response sempre separados.** Nunca o mesmo modelo.
- Naming: `Create<R>Request`, `Update<R>Request`, `<R>Response`, `<R>SummaryResponse`, `<R>FilterRequest`.
- Response herda de `_BaseSchema` (ou `shared.types.BaseSchema`) com `from_attributes=True`.
- Money é `**Decimal`**, nunca `float`. IDs auto-increment são `int` com `Field(..., gt=0)`.
- Validators levantam `ValueError` (Pydantic converte para `RequestValidationError` → HTTP 422).
- **Nunca expor** `password_hash`, tokens ou campos internos em `*Response`.

### Dependencies (`dependencies.py`)

- Expõe providers `get_<feature>_repository` e `get_<feature>_service`.
- FastAPI `Depends()` faz o wiring no controller.
- Repository recebe `db: Prisma = Depends(get_db)`; service recebe `repository: <X>Protocol = Depends(get_<feature>_repository)`.

### Router (`router.py`)

- Para módulos com **um único controller** (caso comum), o controller já declara `router = APIRouter(prefix=..., tags=[...])` com os handlers; `router.py` apenas re-exporta para manter a interface estável:

  ```python
  # router.py
  from src.modules.<feature>.controller import router
  __all__ = ["router"]
  ```

- Para módulos com **múltiplos controllers** (ex.: split por sub-recurso), `router.py` agrega via `include_router`. Nesse caso, cada sub-controller precisa declarar **prefix próprio não vazio** (ex.: `APIRouter(prefix="/items")`); o FastAPI 0.136+ rejeita `include_router` quando sub-router e handler têm path vazios simultaneamente.
- Registrado no [src/main.py](../../src/main.py) via `app.include_router(<feature>_router)`.

---

## 5. Persistência com Prisma

### 5.1. Localização e comandos

- **Schema único** em [src/infra/prisma/schema.prisma](../../src/infra/prisma/schema.prisma).
- **Migrations** em [src/infra/prisma/migrations/](../../src/infra/prisma/migrations/), geradas por `uv run poe prisma-migrate-dev`.
- **Client gerado** via `uv run poe prisma-generate` (necessário após alterar `schema.prisma`).
- Os comandos vivem em `[tool.poe.tasks]` no [pyproject.toml](../../pyproject.toml) e usam `--schema=src/infra/prisma/schema.prisma`.

### 5.2. Regra crítica de fronteira

**Apenas `repository.py` importa Prisma.** Service e controller dependem do repository via `Protocol`. Isso:

- Mantém o service mockável sem precisar do Prisma client.
- Garante que mudanças no Prisma (schema, geração) só impactem a camada de acesso.
- Cria espaço para trocar de ORM no futuro com impacto contido.

Como Python não tem `private`/`internal`, a fronteira depende de **disciplina + code review** (futuramente pode ser imposta por `import-linter` — ver [roadmap](#11-roadmap-aspiracional)).

### 5.3. Lifecycle do client

O client Prisma é um **singleton de processo** em [src/infra/database.py](../../src/infra/database.py), conectado no startup e desconectado no shutdown via `lifespan` do FastAPI:

```python
# src/infra/database.py (já existente)
from contextlib import asynccontextmanager
from prisma import Prisma

from src.core.logger import logger

db = Prisma()


async def get_db() -> Prisma:
    return db


@asynccontextmanager
async def lifespan(app):
    await db.connect()
    logger.info("Connected to database")
    yield
    await db.disconnect()
    logger.info("Disconnected from database")
```

E em [src/main.py](../../src/main.py): `app = FastAPI(lifespan=lifespan)`.

**Não chamar `connect()`/`disconnect()` em testes ou fora do lifespan.** Para testes de integração, ver seção 9 — o `conftest.py` da suíte de integração gerencia uma conexão própria com escopo de sessão.

### 5.4. Repository com Protocol

Padrão obrigatório — Protocol + classe concreta no mesmo arquivo. O service depende do Protocol:

```python
# src/modules/<feature>/repository.py
from typing import Protocol

from prisma import Prisma

from src.modules.<feature>.schema import Create<Feature>Request


class <Feature>RepositoryProtocol(Protocol):
    async def create(self, data: Create<Feature>Request) -> dict: ...
    async def find_by_id(self, <feature>_id: int) -> dict | None: ...


class <Feature>Repository:
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def create(self, data: Create<Feature>Request) -> dict:
        return await self._db.<feature>.create(data={"name": data.name})

    async def find_by_id(self, <feature>_id: int) -> dict | None:
        return await self._db.<feature>.find_unique(where={"id": <feature>_id})
```

### 5.5. Tipos de retorno

- **Repository retorna `dict` ou `dict | None`** — o resultado bruto do Prisma. **Nunca Pydantic.**
- O **service** converte para `*Response` via `<Response>.model_validate(raw)`.
- Isso evita acoplar a camada de I/O ao schema Pydantic e mantém o repository plugável.


| Tipo no banco    | Tipo no dict retornado         | Tipo no DTO Pydantic             |
| ---------------- | ------------------------------ | -------------------------------- |
| `Int`            | `int`                          | `int`                            |
| `String`         | `str`                          | `str` ou `EmailStr`              |
| `Decimal(10, 2)` | `Decimal`                      | `Decimal` (nunca `float`)        |
| `DateTime`       | `datetime`                     | `datetime` (alias se snake_case) |
| Relação          | `dict` aninhado (se `include`) | `<Sub>Response` aninhado         |
| Enum             | `str` (valor do enum)          | `Enum` Python                    |


> **Money sempre `Decimal`.** Prisma retorna `Decimal` nativamente se o campo for `@db.Decimal(...)`; perder isso para `float` trunca centavos.

### 5.6. Relations e `include`

Para trazer dados relacionados em uma só query, use `include`:

```python
async def find_with_items(self, order_id: int) -> dict | None:
    return await self._db.order.find_unique(
        where={"id": order_id},
        include={"items": True, "customer": True},
    )
```

O dict resultante terá `items` (lista de dicts) e `customer` (dict). O service converte para `OrderResponse` com `OrderItemResponse` aninhado.

**Evitar N+1**: se vai usar a relação, traga via `include`. Não chamar `find_`* em loop dentro do service.

### 5.7. Transações multi-write

Quando uma operação envolve **múltiplos writes que precisam ser atômicos**, usar `db.tx()` (interactive transaction):

```python
async def create_order_with_items(
    self,
    order_data: dict,
    items_data: list[dict],
) -> dict:
    async with self._db.tx() as tx:
        order = await tx.order.create(data=order_data)
        await tx.orderitem.create_many(
            data=[{**item, "order_id": order.id} for item in items_data],
        )
        return await tx.order.find_unique(
            where={"id": order.id},
            include={"items": True},
        )
```

**Regras:**

- Transação fica **no repository**, não no service. O service chama um único método de repositório que encapsula a unidade transacional.
- Não cruzar transações entre repositories de módulos diferentes. Se a operação for cross-module, a regra é repensar a fronteira (talvez evento assíncrono em vez de write síncrono).
- Não capturar exceção dentro do `async with tx`: deixar propagar para o rollback acontecer.

### 5.8. Mapeamento de erros do Prisma

O Prisma Python lança exceções específicas quando o banco rejeita uma operação. **Repository captura e traduz para `DomainError`** — service e controller nunca veem exceção do Prisma:


| Exceção Prisma                                   | Significado                                       | Traduzir para                                            |
| ------------------------------------------------ | ------------------------------------------------- | -------------------------------------------------------- |
| `prisma.errors.RecordNotFoundError` (P2025)      | `update`/`delete` em registro inexistente         | `NotFoundError`                                          |
| `prisma.errors.UniqueViolationError` (P2002)     | Constraint UNIQUE violada (email duplicado, etc.) | `ConflictError`                                          |
| `prisma.errors.ForeignKeyViolationError` (P2003) | FK aponta para registro inexistente               | `ConflictError` ou `NotFoundError` (depende do contexto) |
| `prisma.errors.PrismaError` (genérica)           | Outras falhas do client                           | Deixar propagar — handler global retorna 500             |


Exemplo:

```python
# src/modules/users/repository.py
from prisma import Prisma
from prisma.errors import UniqueViolationError

from src.core.exceptions import ConflictError


class UserRepository:
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def create(self, data: CreateUserRequest) -> dict:
        try:
            return await self._db.user.create(
                data={"email": data.email, "name": data.name},
            )
        except UniqueViolationError as exc:
            raise ConflictError(f"User with email {data.email} already exists") from exc
```

**Alternativa preferida quando possível: verificar antes de escrever** (`find_unique` para checar unicidade) — mais explícito, menos `try/except` no repository. Use a tradução de erro apenas quando a verificação prévia for cara ou cria race condition.

### 5.9. Convenções de schema.prisma

- `**@map`/`@@map`** para nomes em snake_case no banco mesmo com camelCase no client (`createdAt` no Prisma → `created_at` no MySQL).
- `**@@index**` em colunas usadas em filtros frequentes.
- `**@@unique**` para chaves de negócio (ex: `email` do usuário).
- **FKs explícitas** com `@relation(fields: [...], references: [...])`.
- **Decimais para dinheiro**: `Decimal @db.Decimal(10, 2)`.
- **Soft delete** quando aplicável: `deletedAt DateTime? @map("deleted_at")` + queries com `where: {"deletedAt": None}`.

---

## 6. Tratamento de erros

Hierarquia em [src/core/exceptions.py](../../src/core/exceptions.py):


| Exceção             | Status HTTP   | Quando lançar                                           |
| ------------------- | ------------- | ------------------------------------------------------- |
| `NotFoundError`     | 404           | Recurso não existe                                      |
| `ConflictError`     | 409           | Estado conflitante (nome duplicado, transição inválida) |
| `ValidationError`   | 422           | Regra de negócio violada (não validação de formato)     |
| `UnauthorizedError` | 401           | Autenticação ausente/inválida                           |
| `DomainError`       | 400 (default) | Erro de domínio genérico                                |


Handlers globais já registrados em [src/main.py](../../src/main.py) traduzem essas exceções para um payload uniforme:

```json
{"error": {"code": "NOT_FOUND", "message": "...", "details": null}}
```

**Service lança, controller nunca captura.** Se precisar de um status novo, criar subclasse de `DomainError` em `src/core/exceptions.py`.

---

## 7. Injeção de dependências

Composição manual com `Depends` do FastAPI — **sem framework de DI externo**. O wiring vive em `dependencies.py` por módulo. Use `Annotated[T, Depends(...)]` para todos os providers e handlers:

```python
# src/modules/<feature>/dependencies.py
from typing import Annotated

from fastapi import Depends
from prisma import Prisma

from src.infra.database import get_db
from src.modules.<feature>.repository import (
    <Feature>Repository,
    <Feature>RepositoryProtocol,
)
from src.modules.<feature>.service import <Feature>Service


def get_<feature>_repository(
    db: Annotated[Prisma, Depends(get_db)],
) -> <Feature>RepositoryProtocol:
    return <Feature>Repository(db)


def get_<feature>_service(
    repository: Annotated[<Feature>RepositoryProtocol, Depends(get_<feature>_repository)],
) -> <Feature>Service:
    return <Feature>Service(repository)
```

> `get_db` já existe em `src/infra/database.py`; reaproveite, não duplique.

Vantagens: nenhuma mágica, dependência explícita, fácil de mockar nos testes (override de `Depends`).

---

## 8. Comunicação entre módulos

Em ordem crescente de desacoplamento:

1. **Chamada direta via Protocol importado.** `OrderService` recebe `UserRepositoryProtocol` (importado de `src/modules/users/repository.py`) via `__init__`. O wiring é feito no `dependencies.py` do consumidor. Síncrono, fortemente tipado, simples — apropriado para a maioria dos casos atuais.
2. **RabbitMQ (assíncrono).** Para operações cross-module que toleram processamento desacoplado: notificações, eventos de auditoria, fan-out. Producer publica do service; consumer vive num módulo dedicado.
3. **Cache via Redis.** Reads pesados, dados que mudam poucas vezes por dia e toleram staleness curta.

> Regra: importar **Protocol**, não classe concreta, entre módulos. Mantém a inversão de dependência viva.

---

## 9. Testes

Dois níveis com diretórios separados:


| Nível           | Diretório                    | Quando rodar            | Característica                                  |
| --------------- | ---------------------------- | ----------------------- | ----------------------------------------------- |
| **Unit**        | `test/unit/<mirror>/`        | Sempre, rápido          | Mocks via `spec=`, sem I/O externo              |
| **Integration** | `test/integration/<mirror>/` | `pytest -m integration` | Prisma + MySQL real (`docker compose up mysql`) |


### Convenções comuns

- **AAA** (Arrange/Act/Assert) com linhas em branco entre os blocos.
- **Naming**: `test_<verb>_<expected>_when_<condition>`.
- **Cada `test_*` ≤ ~15 linhas.** Se passar, extrair builder/fixture.
- **Sem `Any`**. Fixtures e mocks têm tipo anotado.
- **Mocks com `spec=<Class|Protocol>`**. Nunca `MagicMock()` cru.
- **Async**: `AsyncMock` para coroutines; assertions com `assert_awaited_once_with`.
- **Magic values hoisted** como constantes no topo.
- **Cobertura mínima**: ≥ 1 happy path + ≥ 1 erro (404/409/422) por método público.

### Factories para mocks e dados de teste

Objetos de mock e DTOs reaproveitados entre testes são criados exclusivamente por **factory functions** em `test/factories/<feature>.py`, expostas pelo barrel `test/factories/__init__.py`. Testes nunca redefinem helpers locais (`_raw_*`, `_make_*`, `_seed_*`, `_user_response`, etc.) quando já existe factory para a entidade.

- **Localização**: `test/factories/<feature>.py` (espelha `src/modules/<feature>/`). Barrel `test/factories/__init__.py` re-exporta as factories públicas para imports curtos: `from test.factories import make_user_row`.
- **Assinatura padrão**: `def make_<entity>_<variant>(*, <defaults>, **overrides) -> <Type>` — todos os parâmetros são **keyword-only**, têm default sensato, retorno anotado, sem `Any`.
- **Três variantes por feature**:
  - **Row** — `make_<entity>_row(...) -> SimpleNamespace`, mimetiza a forma de um result do Prisma (atributos camelCase como `hashedPassword`, `createdAt`, `deletedAt`). Usar em unit tests de service/repository que mockam o retorno do client Prisma.
  - **DTO** — `make_<entity>_response(...) -> <Entity>Response`, `make_create_<entity>_request(...) -> Create<Entity>Request`, etc. Pydantic v2 instanciado com defaults válidos. Usar em unit tests de controller/schema (path feliz) e como source-of-truth de payloads em integration tests.
  - **Seed** — `async def seed_<entity>(db: Prisma, *, ..., **overrides) -> <PrismaModel>`. Escreve no banco real (`db.<table>.create(...)`). Usar em integration tests quando o setup precisa de dados sem passar pelo endpoint HTTP.
- **Quando é aceitável manter helper local**: helpers que **não** criam dados de domínio — `_create_user_via_http(client, **overrides)` orquestra HTTP + assert 201; `_make_service()` monta SUT + mocks. Esses ficam no arquivo de teste.
- **Tests de validação que precisam de payload inválido de propósito** não usam factory (a factory validaria antes do `pytest.raises`): construir dict cru no próprio teste.

> Adicionou uma feature nova? Criar `test/factories/<feature>.py` com as três variantes e registrar o barrel no mesmo PR — a skill `create-module` já gera o scaffold.

### Integration

- Marker `@pytest.mark.integration` (ou `pytestmark` no módulo) — permite excluir do CI rápido (`pytest -m "not integration"`).
- `conftest.py` expõe fixtures `db`, `client` (httpx `AsyncClient`) e `clean_database` autouse.
- **Banco de teste isolado** (`DATABASE_URL_TEST`) — nunca rodar contra o MySQL de desenvolvimento.
- **Asserts em ambos os lados**: HTTP response **e** estado persistido no DB.

---

## 10. Armadilhas conhecidas

- **Importar Prisma em service/controller** — só repository.
- `**HTTPException` em service** — usar `DomainError`/subclasses.
- `**@staticmethod` em service** — quebra DI e mock.
- **Mesmo modelo Pydantic para Request e Response** — sempre separar.
- `**float` para dinheiro** — sempre `Decimal`.
- **Repository retornando Pydantic** — devolve dict, service converte.
- **Endpoint sem anotação de retorno** — sem `-> <Response>` (ou `response_model=` legado), FastAPI vaza qualquer coisa que o service devolva.
- **`Depends()` como default** (`x: T = Depends(...)`) em vez de `Annotated[T, Depends(...)]` — funciona mas o linter (python:S8410) flaga; prefira sempre `Annotated`.
- `**Mock()` sem `spec**` — esconde refactor breakage.
- `**dict/SimpleNamespace cru em teste quando há factory disponível** — duplicação esconde drift de schema; sempre usar `make_<entity>_*()` do barrel `test/factories/`.
- **PATCH sem `exclude_unset=True`** — campos não enviados viram `null` e sobrescrevem dados.
- `**shared/` crescendo sem critério** — antes de adicionar algo, pergunte: "isso é genuinamente transversal, ou só não decidi a qual módulo pertence?".
- **"Tudo é use case"** — para reads triviais, controller → service → repository é suficiente; não inventar camada extra.

---

## 11. Roadmap aspiracional

O padrão atual (módulo flat com `router/controller/service/repository/schema/dependencies`) atende o estágio do projeto. À medida que o domínio crescer e a complexidade interna de módulos aumentar, vale considerar a evolução para uma estrutura DDD-style com camadas explícitas:

```
src/modules/<feature>/
├── domain/
│   ├── entities.py
│   ├── value_objects.py
│   └── events.py
├── application/
│   ├── use_cases.py
│   └── ports.py        # Protocols
├── adapters/
│   ├── http.py         # FastAPI router/controller
│   └── repositories.py # Prisma impls
└── infrastructure/
    └── config.py
```

**Gatilhos para considerar a migração:**

- Algum módulo passa a ter > 10 endpoints e a regra de negócio fica densa demais para um único `service.py`.
- Aparece necessidade clara de **entidades imutáveis com invariantes** (value objects), que ficam awkward dentro de schemas Pydantic.
- Surge necessidade de **eventos de domínio** in-process entre módulos.
- O time decide impor fronteiras automaticamente via `[import-linter](https://import-linter.readthedocs.io/)`, o que combina melhor com a estrutura em camadas pastas.

**Quando isso acontecer**, abrir um novo ADR (`0002-...`) registrando:

- Quais módulos migram (incremental, não big-bang).
- Como `api.py` substitui o import direto via `Protocol`.
- Convenção sobre `shared_kernel` para tipos genuinamente transversais.
- Configuração do `import-linter` com contratos `independence` + `layers`.

Até lá, o padrão flat documentado nas seções 1–10 é a referência.

---

## 12. Ferramentas

- `ruff` — lint e format.
- `mypy` — typing (gate no CI).
- `pytest` + `pytest-asyncio` + `httpx` — testes.
- `prisma` (Python) — ORM e migrations.
- `loguru` — logging.
- `pre-commit` — gates locais antes do push.

---

## 13. Referências internas

- Skills: `[.claude/skills/create-module/SKILL.md](../../.claude/skills/create-module/SKILL.md)`, `[create-endpoint](../../.claude/skills/create-endpoint/SKILL.md)`, `[pydantic-schema](../../.claude/skills/pydantic-schema/SKILL.md)`, `[pytest-unit](../../.claude/skills/pytest-unit/SKILL.md)`, `[pytest-integration](../../.claude/skills/pytest-integration/SKILL.md)`.
- Agents: `[fastapi-architect](../../.claude/agents/fastapi-architect.md)`, `[pizzaria-reviewer](../../.claude/agents/pizzaria-reviewer.md)`.
- ADR raiz: `[docs/adr/0001-adotar-modular-monolith-em-camadas.md](../adr/0001-adotar-modular-monolith-em-camadas.md)`.

