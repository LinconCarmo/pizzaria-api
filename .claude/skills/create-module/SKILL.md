---
name: create-module
description: Cria um módulo feature completo em src/modules/<feature>/ seguindo o padrão Layered Modular Monolith do pizzaria-api (router, controller, service, repository, schema, dependencies). Use quando o usuário pedir "criar módulo X", "adicionar feature X", "scaffold de módulo", "novo bounded context", ou quando o módulo destino não existe ainda em src/modules/.
---

# Create Module Skill

Use esta skill para fazer scaffold de um novo módulo feature em `src/modules/<feature>/` seguindo o padrão **Layered Modular Monolith** ("NestJS-like" em FastAPI) do pizzaria-api.

> Referência arquitetural: [`docs/architecture/modular-monolith.md`](../../../docs/architecture/modular-monolith.md) (seções 3–4). Decisão: [ADR 0001](../../../docs/adr/0001-adotar-modular-monolith-em-camadas.md).

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
├── __init__.py                 # vazio (apenas marker de package)
├── controllers/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       └── <feature>.py        # APIRouter — prefix do recurso, tags, handlers HTTP
├── router.py                   # agrega controllers/v1/<feature>.py (e futuras versões)
├── service.py                  # regra de negócio — orquestra repository, lança DomainError
├── repository.py               # acesso a Prisma — define Protocol + implementação
├── schema.py                   # DTOs Pydantic v2 — *Request / *Response
└── dependencies.py             # FastAPI Depends() — wiring repository → service
```

**Naming**:

- Arquivos curtos, sem prefixo do nome do módulo na raiz. O diretório já dá contexto.
- O arquivo dentro de `controllers/v1/` é `<feature>.py` (PT recurso, ex.: `orders.py`, `users.py`) — permite, no futuro, adicionar mais controllers na mesma `v1` (ex.: `sessions.py`) sem renomear.

- ✅ `src/modules/orders/controllers/v1/orders.py`
- ❌ `src/modules/orders/controllers/v1/orders.controller.py`
- ❌ `src/modules/orders/orders_controller.py`

**Versionamento de URL**: o prefixo `/api/v1` é aplicado **em [`src/main.py`](../../../src/main.py)** no `include_router`, **não** dentro do controller. O controller declara apenas `prefix="/<feature>"`. Exceção: `/health` é incluído **sem** `prefix=` (probes de infra não devem quebrar entre versões).

## Templates

Substitua `<feature>` pelo nome em snake_case (ex: `orders`) e `<Feature>` pelo PascalCase singular do recurso (ex: `Order`).

### `__init__.py`

```python
```

(arquivo vazio)

### `schema.py`

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

### `repository.py`

```python
from typing import Protocol
from uuid import UUID

from prisma import Prisma

from src.modules.<feature>.schema import Create<Feature>Request


class <Feature>RepositoryProtocol(Protocol):
    async def create(self, data: Create<Feature>Request) -> dict: ...
    async def find_by_id(self, <feature>_id: UUID) -> dict | None: ...
    async def find_many(self) -> list[dict]: ...


class <Feature>Repository:
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def create(self, data: Create<Feature>Request) -> dict:
        return await self._db.<feature>.create(
            data={"name": data.name},
        )

    async def find_by_id(self, <feature>_id: UUID) -> dict | None:
        return await self._db.<feature>.find_unique(
            where={"id": str(<feature>_id)},
        )

    async def find_many(self) -> list[dict]:
        return await self._db.<feature>.find_many()
```

> **UUID → str na borda.** O Prisma client espera `str` em `where={"id": ...}` para colunas `String`. Converter com `str(<feature>_id)` aqui no repository; service e controller seguem com `UUID`.

> **Regra crítica**: este é o **único** arquivo do módulo que pode importar `prisma`. Service e controller NÃO importam Prisma.

### `service.py`

```python
from uuid import UUID

from src.core.exceptions import NotFoundError
from src.modules.<feature>.repository import <Feature>RepositoryProtocol
from src.modules.<feature>.schema import Create<Feature>Request, <Feature>Response


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

### `dependencies.py`

```python
from fastapi import Depends
from prisma import Prisma

from src.infra.database import db
from src.modules.<feature>.repository import <Feature>Repository, <Feature>RepositoryProtocol
from src.modules.<feature>.service import <Feature>Service


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

### `controllers/v1/<feature>.py`

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.core.exceptions import ErrorResponse
from src.modules.<feature>.dependencies import get_<feature>_service
from src.modules.<feature>.schema import Create<Feature>Request, <Feature>Response
from src.modules.<feature>.service import <Feature>Service

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

### `router.py`

```python
from fastapi import APIRouter

from src.modules.<feature>.controllers.v1.<feature> import router as <feature>_v1

router = APIRouter()
router.include_router(<feature>_v1)

__all__ = ["router"]
```

> `router.py` é o ponto estável importado por `main.py` — futuras `controllers/v2/` entram aqui via `include_router(...)` adicional sem mexer em `main.py`.

## Wiring no `src/main.py`

Adicionar dois pontos:

```python
# import perto dos outros routers
from src.modules.<feature>.router import router as <feature>_router

# include com prefixo de versão (exceção: /health vai SEM prefix=)
app.include_router(<feature>_router, prefix="/api/v1")
```

## Factories para testes (`test/factories/<feature>.py`)

Toda feature nova precisa expor factories para os testes (`pytest-unit` e `pytest-integration` exigem). Criar **junto** com o scaffold do módulo — não deixar para depois. Ver §10 "Factories" em [`docs/architecture/modular-monolith.md`](../../../docs/architecture/modular-monolith.md).

### Template `test/factories/<feature>.py`

```python
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from prisma import Prisma

from src.modules.<feature>.schema import (
    Create<Feature>Request,
    <Feature>Response,
)

NOW = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)


def make_<feature>_row(
    *,
    id: int = 1,
    name: str = "Margherita",
    created_at: datetime = NOW,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        name=name,
        createdAt=created_at,
    )


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
    **overrides: Any,
) -> Any:
    data: dict[str, Any] = {"name": name, **overrides}
    return await db.<feature>.create(data=cast(Any, data))
```

### Registrar no barrel `test/factories/__init__.py`

Adicionar as factories no `__init__.py`:

```python
from test.factories.<feature> import (
    make_create_<feature>_request,
    make_<feature>_response,
    make_<feature>_row,
    seed_<feature>,
)
```

E incluir os nomes em `__all__`.

## Verification

Antes de reportar como pronto, rodar e validar:

1. **Imports limpos**: `uv run ruff check src/modules/<feature>/` → 0 erros.
2. **Typing limpo**: `uv run mypy src/modules/<feature>/` → 0 erros.
3. **App sobe**: `uv run uvicorn src.main:app --reload` inicia sem erro de import.
4. **OpenAPI**: abrir `http://localhost:8000/docs` e confirmar que aparecem rotas `POST /api/v1/<feature>s`, `GET /api/v1/<feature>s/{id}`, `GET /api/v1/<feature>s`.
5. **Smoke HTTP**: `curl -X POST http://localhost:8000/api/v1/<feature>s -H 'Content-Type: application/json' -d '{"name":"X"}'` retorna 201 com `id` e `created_at`.

Se o usuário não pediu CRUD completo, ajuste — a skill scaffolda CRUD básico; remova endpoints/métodos não solicitados antes de entregar.

## Common pitfalls

- **Importar Prisma em `service.py` ou `controller.py`** — Prisma só em `repository.py`. Quebra inversão de dependência e dificulta mocks.
- **Usar `@staticmethod` no service** (estilo `HealthService.check()`) — service deve ser instanciado via DI; staticmethod impede mock e injeção.
- **`HTTPException` no controller** — usar `DomainError` (ou subclasses como `NotFoundError`, `ConflictError`) no service. Handlers globais já estão registrados em `src/main.py`.
- **Pydantic model único para Request + Response** — sempre separar. Request define o que entra (sem `id`, `created_at`), Response define o que sai (com metadados).
- **Prefixo no nome do arquivo** (`orders.controller.py`) — usar `controller.py`. O `users/` antigo do projeto usa o padrão NestJS-style; isso é legado e não deve ser replicado.
- **Esquecer `app.include_router(<feature>_router)` em `src/main.py`** — sem isso o módulo existe mas não responde.
- **Esquecer `__init__.py`** vazio dentro do módulo — Python 3.13 ainda exige para imports relativos consistentes.

## Verification checklist (antes de entregar)

- [ ] Diretório `src/modules/<feature>/` criado com layout: `__init__.py`, `router.py`, `service.py`, `repository.py`, `schema.py`, `dependencies.py` + `controllers/__init__.py`, `controllers/v1/__init__.py`, `controllers/v1/<feature>.py`.
- [ ] Nomes de arquivo **sem** prefixo do módulo na raiz; arquivo em `controllers/v1/` segue o nome do recurso (`<feature>.py`).
- [ ] `repository.py` é o único arquivo que importa `prisma`.
- [ ] Service usa `<Feature>RepositoryProtocol`, não a classe concreta.
- [ ] Nenhum `@staticmethod`, nenhum `HTTPException` no controller.
- [ ] Schemas separados: `Create<Feature>Request`, `<Feature>Response` (e `Update<Feature>Request` se aplicável).
- [ ] `src/main.py` inclui o novo `<feature>_router` com `prefix="/api/v1"` (`/health` é exceção).
- [ ] `test/factories/<feature>.py` criado com `make_<feature>_row`, `make_<feature>_response`, `make_create_<feature>_request`, `async seed_<feature>`.
- [ ] `test/factories/__init__.py` re-exporta as factories novas e atualiza `__all__`.
- [ ] `ruff check` e `mypy` limpos.
- [ ] `/docs` lista as rotas novas sob `/api/v1/...`.
