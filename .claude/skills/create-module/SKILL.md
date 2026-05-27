---
name: create-module
description: Cria um módulo feature completo em src/modules/<feature>/ seguindo o padrão Layered Modular Monolith do pizzaria-api (router, controller, service, repository, schema, dependencies). Use quando o usuário pedir "criar módulo X", "adicionar feature X", "scaffold de módulo", "novo bounded context", ou quando o módulo destino não existe ainda em src/modules/.
---

# Create Module Skill

Use esta skill para fazer scaffold de um novo módulo feature em `src/modules/<feature>/` seguindo o padrão **Layered Modular Monolith** ("NestJS-like" em FastAPI) do pizzaria-api.

> Regras normativas: [conventions.md](../../../docs/architecture/conventions.md). Detalhe/templates: [modular-monolith.md](../../../docs/architecture/modular-monolith.md) (seções 3–4). Decisões: [ADR 0001](../../../docs/adr/0001-adotar-modular-monolith-em-camadas.md), [ADR 0003](../../../docs/adr/0003-ids-uuid.md), [ADR 0004](../../../docs/adr/0004-naming-com-prefixo-de-entidade.md).

## Quando usar

- "Crie o módulo orders / products / payments / customers"
- "Scaffold da feature de pedidos"
- "Adicionar bounded context X"
- Qualquer pedido que implique criar uma nova feature ainda inexistente em `src/modules/`

## Quando NÃO usar

- Se o diretório `src/modules/<feature>/` **já existe** → use a skill `create-endpoint` para adicionar novos endpoints.
- Se for apenas adicionar um schema/DTO sem rota nova → use `pydantic-schema`.
- Se for apenas adicionar exceção de domínio → editar `src/core/exceptions.py` diretamente.

## Pre-flight checklist

Antes de criar qualquer arquivo, valide:

1. **Nome do módulo**: snake_case, plural quando representa recurso (`orders`, `products`, `users`), singular para conceitos (`auth`, `billing`).
2. **Diretório não existe**: `ls src/modules/<feature>` deve falhar. Se existir, parar e perguntar ao usuário.
3. **Modelo Prisma**: confirmar que `src/infra/prisma/schema.prisma` já tem o modelo necessário. Se não tiver:
   - Perguntar ao usuário se ele quer que o modelo seja adicionado agora.
   - Se sim: adicionar ao schema, rodar `uv run prisma migrate dev --schema=src/infra/prisma/schema.prisma --name add_<feature>` e `uv run prisma generate --schema=src/infra/prisma/schema.prisma` antes de continuar.
   - **PK obrigatória**: `id String @id @default(uuid()) @db.Char(36)` (ver [ADR 0003](../../../docs/adr/0003-ids-uuid.md)). Nunca `Int @id @default(autoincrement())`.
4. **Bootstrap atual**: verificar `src/main.py` para entender onde registrar o novo router (`app.include_router(...)`).

## Estrutura do módulo (obrigatória)

```
src/modules/<feature>/
├── __init__.py                       # vazio (apenas marker de package)
├── controllers/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       └── <entity>_controller.py    # APIRouter — prefix do recurso, tags, handlers HTTP
├── <entity>_router.py                # agrega controllers/v1/<entity>_controller.py (e futuras versões)
├── <entity>_service.py               # regra de negócio — orquestra repository, lança DomainError
├── <entity>_repository.py            # acesso a Prisma — define Protocol + implementação
├── <entity>_schema.py                # DTOs Pydantic v2 — *Request / *Response
└── <entity>_dependencies.py          # FastAPI Depends() — wiring repository → service
```

> Regra completa: [conventions.md#estrutura](../../../docs/architecture/conventions.md#estrutura) e [conventions.md#naming](../../../docs/architecture/conventions.md#naming).

**Naming** (resumo): arquivos `snake_case` prefixados pela entidade — diretório plural (`orders`), prefixo singular (`order_service.py`, `controllers/v1/order_controller.py`). Regra completa: [conventions.md#naming](../../../docs/architecture/conventions.md#naming).

**Versionamento de URL**: o prefixo `/api/v1` é aplicado **em [`src/main.py`](../../../src/main.py)** no `include_router`, **não** dentro do controller. O controller declara apenas `prefix="/<feature>"`. Exceção: `/health` é incluído **sem** `prefix=` (probes de infra não devem quebrar entre versões).

## Templates

Substitua `<feature>` pelo nome do módulo em snake_case plural (ex: `orders`), `<entity>` pelo singular usado no prefixo dos arquivos (ex: `order`) e `<Feature>` pelo PascalCase singular do recurso (ex: `Order`). Os nomes de **classe** permanecem PascalCase prefixados (`OrderService`, `OrderRepository`, `CreateOrderRequest`) — só o nome do **arquivo** vira `<entity>_<layer>.py`.

### `__init__.py`

```python
```

(arquivo vazio)

### `<entity>_schema.py`

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class Create<Feature>Request(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        examples=["Margherita"],
        description="Nome do <feature>",
    )


class <Feature>Response(_BaseSchema):
    id: UUID = Field(..., examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"])
    name: str = Field(..., examples=["Margherita"])
    created_at: datetime = Field(..., alias="createdAt")
```

> Se `src/shared/types.py` já tiver um `BaseSchema` reutilizável, importe de lá em vez de redefinir `_BaseSchema`.

### `<entity>_repository.py`

```python
from typing import Protocol
from uuid import UUID

from prisma import Prisma

from src.modules.<feature>.<entity>_schema import Create<Feature>Request


class <Feature>RepositoryProtocol(Protocol):
    async def create(self, data: Create<Feature>Request) -> dict[str, object]: ...
    async def find_by_id(self, <feature>_id: UUID) -> dict[str, object] | None: ...
    async def find_many(self) -> list[dict[str, object]]: ...


class <Feature>Repository:
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def create(self, data: Create<Feature>Request) -> dict[str, object]:
        created = await self._db.<feature>.create(
            data={"name": data.name},
        )
        return created.model_dump()

    async def find_by_id(self, <feature>_id: UUID) -> dict[str, object] | None:
        row = await self._db.<feature>.find_unique(
            where={"id": str(<feature>_id)},
        )
        return row.model_dump() if row is not None else None

    async def find_many(self) -> list[dict[str, object]]:
        rows = await self._db.<feature>.find_many()
        return [row.model_dump() for row in rows]
```

> **UUID → str só na borda do repository** (`where={"id": str(<feature>_id)}`); service e controller seguem com `UUID`. Regra: [conventions.md#uuid](../../../docs/architecture/conventions.md#uuid).

> **Use `dict[str, object]`, nunca `dict` puro** — o `mypy --strict` do projeto liga `disallow_any_generics`. Serialize o retorno do Prisma com `.model_dump()` para não devolver `prisma.models.*` (senão o service teria de importar Prisma). Regra: [conventions.md#camadas](../../../docs/architecture/conventions.md#camadas).

> **Regra crítica**: este é o **único** arquivo do módulo que pode importar `prisma`. Service e controller NÃO importam Prisma.

### `<entity>_service.py`

```python
from uuid import UUID

from src.core.exceptions import NotFoundError
from src.modules.<feature>.<entity>_repository import <Feature>RepositoryProtocol
from src.modules.<feature>.<entity>_schema import Create<Feature>Request, <Feature>Response


class <Feature>Service:
    def __init__(self, repository: <Feature>RepositoryProtocol) -> None:
        self._repository = repository

    async def create(self, data: Create<Feature>Request) -> <Feature>Response:
        entity = await self._repository.create(data)
        return <Feature>Response.model_validate(entity)

    async def get_by_id(self, <feature>_id: UUID) -> <Feature>Response:
        entity = await self._repository.find_by_id(<feature>_id)

        if entity is None:
            raise NotFoundError(f"<Feature> {<feature>_id} not found")

        return <Feature>Response.model_validate(entity)

    async def list(self) -> list[<Feature>Response]:
        entities = await self._repository.find_many()
        return [<Feature>Response.model_validate(e) for e in entities]
```

> Service depende do **Protocol** (não da classe concreta), o que facilita mock em testes unitários e mantém a inversão de dependência.

> **`model_validate(entity)` direto só funciona quando os nomes batem.** Se o schema usa `@map` (colunas snake_case viram atributos camelCase no Prisma — `isActive`, `createdAt`) ou há relação aninhada (`role` vira `{"name": ...}`), o service precisa **remapear as chaves para snake_case e achatar a relação** num `dict` antes do `model_validate` — sem reimportar Prisma. Ver [modular-monolith.md §5.5](../../../docs/architecture/modular-monolith.md) para o exemplo (`_to_response`).

### `<entity>_dependencies.py`

```python
from fastapi import Depends
from prisma import Prisma

from src.infra.database import db
from src.modules.<feature>.<entity>_repository import <Feature>Repository, <Feature>RepositoryProtocol
from src.modules.<feature>.<entity>_service import <Feature>Service


def get_db() -> Prisma:
    return db


def get_<feature>_repository(
    db: Prisma = Depends(get_db),
) -> <Feature>RepositoryProtocol:
    return <Feature>Repository(db)


def get_<feature>_service(
    repository: <Feature>RepositoryProtocol = Depends(get_<feature>_repository),
) -> <Feature>Service:
    return <Feature>Service(repository)
```

### `controllers/v1/<entity>_controller.py`

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.core.exceptions import ErrorResponse
from src.modules.<feature>.<entity>_dependencies import get_<feature>_service
from src.modules.<feature>.<entity>_schema import Create<Feature>Request, <Feature>Response
from src.modules.<feature>.<entity>_service import <Feature>Service

router = APIRouter(prefix="/<feature>s", tags=["<Feature>s"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo <feature>",
    responses={
        409: {"model": ErrorResponse, "description": "<Feature> já existe"},
    },
)
async def create_<feature>(
    payload: Create<Feature>Request,
    service: Annotated[<Feature>Service, Depends(get_<feature>_service)],
) -> <Feature>Response:
    return await service.create(payload)


@router.get(
    "/{<feature>_id}",
    summary="Busca um <feature> por ID",
    responses={
        404: {"model": ErrorResponse, "description": "<Feature> não encontrado"},
    },
)
async def get_<feature>(
    <feature>_id: UUID,
    service: Annotated[<Feature>Service, Depends(get_<feature>_service)],
) -> <Feature>Response:
    return await service.get_by_id(<feature>_id)


@router.get(
    "",
    summary="Lista <feature>s",
)
async def list_<feature>s(
    service: Annotated[<Feature>Service, Depends(get_<feature>_service)],
) -> list[<Feature>Response]:
    return await service.list()
```

> O `prefix="/<feature>s"` é só do recurso. URL final = `/api/v1` (aplicado em `main.py`) + `/<feature>s` + path do handler.

> Controllers **não** capturam exceções — handlers globais em `src/main.py` cuidam de `DomainError`, `RequestValidationError` e `Exception`. O `responses=` no decorator é só metadata para o Swagger: ensina o cliente que aqueles status existem; quem dispara continua sendo o service via `DomainError`.

> **Padrão FastAPI moderno**: tipo de retorno via annotation (`-> <Feature>Response`), não `response_model=`. FastAPI ≥ 0.89 gera a mesma OpenAPI a partir da anotação e mantém a tipagem em um lugar só.

### `<entity>_router.py`

```python
from fastapi import APIRouter

from src.modules.<feature>.controllers.v1.<entity>_controller import router as <feature>_v1

router = APIRouter()
router.include_router(<feature>_v1)

__all__ = ["router"]
```

> `<entity>_router.py` é o ponto estável importado por `main.py` — futuras `controllers/v2/` entram aqui via `include_router(...)` adicional sem mexer em `main.py`.

## Wiring no `src/main.py`

Adicionar dois pontos:

```python
# import perto dos outros routers
from src.modules.<feature>.<entity>_router import router as <feature>_router

# include com prefixo de versão (exceção: /health vai SEM prefix=)
app.include_router(<feature>_router, prefix="/api/v1")
```

## Factories para testes (`test/factories/<entity>_factory.py`)

Toda feature nova precisa expor factories (`make_<feature>_row`, `make_<feature>_response`, `make_create_<feature>_request`, `seed_<feature>`) — criar **junto** com o scaffold, keyword-only e sem `Any`. Regra completa: [conventions.md#testes](../../../docs/architecture/conventions.md#testes).

### Template `test/factories/<entity>_factory.py`

```python
from datetime import UTC, datetime
from typing import cast

from prisma import Prisma, types
from prisma.models import <Feature>

from src.modules.<feature>.<entity>_schema import (
    Create<Feature>Request,
    <Feature>Response,
)

NOW = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)


def make_<feature>_row(
    *,
    id: int = 1,
    name: str = "Margherita",
    created_at: datetime = NOW,
) -> dict[str, object]:
    # Espelha o dict bruto do repository (`.model_dump()`), com as chaves no
    # formato do Prisma (camelCase para colunas `@map`). O service lê chaves de dict.
    return {
        "id": id,
        "name": name,
        "createdAt": created_at,
    }


def make_create_<feature>_request(
    *,
    name: str = "Margherita",
) -> Create<Feature>Request:
    return Create<Feature>Request(name=name)


def make_<feature>_response(
    *,
    id: int = 1,
    name: str = "Margherita",
    created_at: datetime = NOW,
) -> <Feature>Response:
    return <Feature>Response(id=id, name=name, created_at=created_at)


async def seed_<feature>(
    db: Prisma,
    *,
    name: str = "Margherita",
    **overrides: object,
) -> <Feature>:
    data: dict[str, object] = {"name": name, **overrides}
    # cast para o type concreto do Prisma (nunca `Any`); o spread de **overrides
    # impede anotar `data` diretamente como types.<Feature>CreateInput.
    return await db.<feature>.create(data=cast(types.<Feature>CreateInput, data))
```

> **Sem `Any`** (resumo): use `object` para kwargs dinâmicos e `cast(types.<Feature>CreateInput, ...)`, nunca `cast(Any, ...)`. `<Feature>` em `-> <Feature>` é `from prisma.models import <Feature>`. Regra completa: [conventions.md#tipos](../../../docs/architecture/conventions.md#tipos).

### Registrar no barrel `test/factories/__init__.py`

Adicionar as factories no `__init__.py`:

```python
from test.factories.<entity>_factory import (
    make_create_<feature>_request,
    make_<feature>_response,
    make_<feature>_row,
    seed_<feature>,
)
```

E incluir os nomes em `__all__`.

## Verification

Antes de reportar como pronto, rodar e validar (atalhos `poe` em [conventions.md#comandos](../../../docs/architecture/conventions.md#comandos)):

1. **Imports limpos**: `uv run ruff check src/modules/<feature>/` → 0 erros.
2. **Typing limpo**: `uv run mypy src/modules/<feature>/` → 0 erros.
3. **App sobe**: `uv run uvicorn src.main:app --reload` inicia sem erro de import.
4. **OpenAPI**: abrir `http://localhost:8000/docs` e confirmar que aparecem rotas `POST /api/v1/<feature>s`, `GET /api/v1/<feature>s/{id}`, `GET /api/v1/<feature>s`.
5. **Smoke HTTP**: `curl -X POST http://localhost:8000/api/v1/<feature>s -H 'Content-Type: application/json' -d '{"name":"X"}'` retorna 201 com `id` e `created_at`.

Se o usuário não pediu CRUD completo, ajuste — a skill scaffolda CRUD básico; remova endpoints/métodos não solicitados antes de entregar.

## Common pitfalls

- **Camadas / DI / erros / naming / Pydantic** — Prisma só no repository, sem `@staticmethod`, sem `HTTPException` (use `DomainError`), Request ≠ Response, separador `_` no nome do arquivo. Regras: [conventions.md#camadas](../../../docs/architecture/conventions.md#camadas), [#di](../../../docs/architecture/conventions.md#di), [#erros](../../../docs/architecture/conventions.md#erros), [#naming](../../../docs/architecture/conventions.md#naming), [#pydantic](../../../docs/architecture/conventions.md#pydantic).
- **Esquecer `app.include_router(<feature>_router)` em `src/main.py`** — sem isso o módulo existe mas não responde.
- **Esquecer `__init__.py`** vazio dentro do módulo — Python 3.13 ainda exige para imports relativos consistentes.

## Verification checklist (antes de entregar)

- [ ] Diretório `src/modules/<feature>/` criado com layout: `__init__.py`, `<entity>_router.py`, `<entity>_service.py`, `<entity>_repository.py`, `<entity>_schema.py`, `<entity>_dependencies.py` + `controllers/__init__.py`, `controllers/v1/__init__.py`, `controllers/v1/<entity>_controller.py`.
- [ ] Arquivos em snake_case prefixados pela entidade (`<entity>_<layer>.py`); controller em `controllers/v1/<entity>_controller.py`.
- [ ] `<entity>_repository.py` é o único arquivo que importa `prisma`.
- [ ] Service usa `<Feature>RepositoryProtocol`, não a classe concreta.
- [ ] Nenhum `@staticmethod`, nenhum `HTTPException` no controller.
- [ ] Schemas separados: `Create<Feature>Request`, `<Feature>Response` (e `Update<Feature>Request` se aplicável).
- [ ] `src/main.py` inclui o novo `<feature>_router` com `prefix="/api/v1"` (`/health` é exceção).
- [ ] `test/factories/<entity>_factory.py` criado com `make_<feature>_row`, `make_<feature>_response`, `make_create_<feature>_request`, `async seed_<feature>`.
- [ ] `test/factories/__init__.py` re-exporta as factories novas e atualiza `__all__`.
- [ ] `ruff check` e `mypy` limpos.
- [ ] `/docs` lista as rotas novas sob `/api/v1/...`.
