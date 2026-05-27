---
name: create-endpoint
description: Adiciona um endpoint a um módulo existente em src/modules/<feature>/ — rota no controller, método no service, schemas Request/Response, e (se necessário) método no repository. Use quando o módulo já existe e o usuário pedir "adicionar endpoint X", "criar rota Y", "novo método na feature Z", "expor operação W via HTTP".
---

# Create Endpoint Skill

Use esta skill quando o módulo **já existe** em `src/modules/<feature>/` e você precisa adicionar mais uma operação HTTP. Para criar um módulo do zero, use a skill `create-module`.

> Regras normativas: [conventions.md](../../../docs/architecture/conventions.md). Detalhe/templates: [modular-monolith.md](../../../docs/architecture/modular-monolith.md) (seções 4 e 6). Decisões: [ADR 0001](../../../docs/adr/0001-adotar-modular-monolith-em-camadas.md), [ADR 0003](../../../docs/adr/0003-ids-uuid.md), [ADR 0004](../../../docs/adr/0004-naming-com-prefixo-de-entidade.md).

## Quando usar

- "Adicionar `PATCH /orders/{id}/cancel`"
- "Criar endpoint de busca por nome em produtos"
- "Expor método X do service via HTTP"
- "Adicionar `DELETE /users/{id}`"

## Quando NÃO usar

- Módulo ainda não existe → `create-module`.
- Mudança não tem rota HTTP (job, listener de RabbitMQ, etc.) → editar service diretamente.
- Apenas alterar Pydantic existente → `pydantic-schema`.

## Pre-flight checklist

1. **Módulo existe**: `ls src/modules/<feature>/controllers/v1/<entity>_controller.py` deve achar o arquivo (controller versionado dentro do módulo). Naming dos arquivos: [conventions.md#naming](../../../docs/architecture/conventions.md#naming).
2. **Operação suportada pelo modelo Prisma**: confirmar que `schema.prisma` tem os campos/relações necessários.
3. **REST coerente**: a nova rota segue o REST plural do módulo? URLs finais são prefixadas com `/api/v1` (aplicado em `src/main.py`):
   - `GET /api/v1/<features>` — listagem
   - `POST /api/v1/<features>` — criação
   - `GET /api/v1/<features>/{id}` — detalhe
   - `PATCH /api/v1/<features>/{id}` — update parcial
   - `DELETE /api/v1/<features>/{id}` — remoção
   - `POST /api/v1/<features>/{id}/<action>` — sub-recurso/ação (cancel, approve, ship)
   - **Exceção**: `/health` fica fora do versionamento.
   - No decorator do handler, o path é **relativo** ao `prefix` do controller (`""`, `"/{id}"`, `"/{id}/cancel"`). O `/<features>` vem do `APIRouter(prefix="/<features>")`; o `/api/v1` vem do `include_router` em `main.py`.
4. **Idempotência**: operações `PUT` e `DELETE` devem ser idempotentes; `POST` cria.

## Fluxo de implementação (bottom-up)

Implemente nesta ordem para manter cada camada tipada e testável de baixo pra cima:

### 1. Schema (`<entity>_schema.py`)

Adicionar (não substituir) os DTOs necessários:

```python
class Update<Feature>Request(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    # campos opcionais para PATCH; usar None como "não alterar"


class <Feature>SummaryResponse(_BaseSchema):
    id: int
    name: str
    # subset enxuto para listagens
```

**Regras** (resumo): `*Request` ≠ `*Response`; `PATCH` com todos os campos opcionais; `*SummaryResponse` para listagens grandes; `examples=[...]` em `Field`. Regra completa: [conventions.md#pydantic](../../../docs/architecture/conventions.md#pydantic).

> Use a skill `pydantic-schema` se a validação for não-trivial (validators, regex, restrições cruzadas).

### 2. Repository (`<entity>_repository.py`)

Se a operação precisa de acesso a dados não coberto, adicionar **tanto no Protocol quanto na classe**:

```python
from uuid import UUID

from prisma import types  # tipar os args do Prisma — nunca dict cru nem cast(Any)


class <Feature>RepositoryProtocol(Protocol):
    # ... existentes ...
    async def update(
        self,
        <feature>_id: UUID,
        *,
        name: str | None = None,
    ) -> dict[str, object]: ...
    async def delete(self, <feature>_id: UUID) -> None: ...


class <Feature>Repository:
    # ... existentes ...
    async def update(self, <feature>_id: UUID, *, name: str | None = None) -> dict[str, object]:
        data: types.<Feature>UpdateInput = {}
        if name is not None:
            data["name"] = name

        row = await self._db.<feature>.update(where={"id": str(<feature>_id)}, data=data)
        if row is None:  # prisma-client-py: update retorna None se não existir
            raise NotFoundError(f"<Feature> {<feature>_id} not found")
        return row.model_dump()

    async def delete(self, <feature>_id: UUID) -> None:
        await self._db.<feature>.delete(where={"id": str(<feature>_id)})
```

**Regras**:
- Métodos do repository retornam `dict[str, object]` (resultado bruto do Prisma via `.model_dump()`), `dict[str, object] | None` ou `None`. **Não retornam Pydantic nem `prisma.models.*`** — quem converte é o service. (`dict` sem parâmetros falha no `mypy --strict`.)
- **Receba campos por keyword (`*, name=None`), não um `dict` cru** — assim você monta um `types.<Feature>UpdateInput` tipado e passa pro Prisma sem `cast(Any)` (um `dict[str, object]` não casa com o `TypedDict` que o Prisma espera).
- Não embutir regra de negócio. Repository é I/O puro.
- Se a query precisa de joins/relations, adicionar `include={"items": True}` no Prisma call.

### 3. Service (`<entity>_service.py`)

Adicionar o método com regra de negócio:

```python
from uuid import UUID

from src.core.exceptions import NotFoundError


class <Feature>Service:
    # ... existentes ...

    async def update(
        self,
        <feature>_id: UUID,
        data: Update<Feature>Request,
    ) -> <Feature>Response:
        patch = data.model_dump(exclude_unset=True)

        if not patch:
            return await self.get_by_id(<feature>_id)

        # repo recebe campos por keyword e levanta NotFoundError se não existir
        entity = await self._repository.update(<feature>_id, **patch)

        return <Feature>Response.model_validate(entity)

    async def delete(self, <feature>_id: UUID) -> None:
        existing = await self._repository.find_by_id(<feature>_id)

        if existing is None:
            raise NotFoundError(f"<Feature> {<feature>_id} not found")

        await self._repository.delete(<feature>_id)
```

**Regras**:
- Lança `DomainError` (ou subclasse) — nunca `HTTPException`.
- `model_dump(exclude_unset=True)` para PATCH (não envia `null` se o cliente não mandou o campo).
- Toda checagem de existência é responsabilidade do service, não do controller.
- Operações que cruzam múltiplos writes → considerar `TransactionRunner` (segunda leva de skills).

### 4. Controller (`controllers/v1/<entity>_controller.py`)

Editar o controller versionado do módulo (`src/modules/<feature>/controllers/v1/<entity>_controller.py`) e adicionar o handler:

```python
from typing import Annotated
from uuid import UUID

from fastapi import Depends, status

from src.core.exceptions import ErrorResponse  # ver §"Documentando erros"


@router.patch(
    "/{<feature>_id}",
    status_code=status.HTTP_200_OK,
    summary="Atualiza parcialmente um <feature>",
    responses={
        404: {"model": ErrorResponse, "description": "<Feature> não encontrado"},
        409: {"model": ErrorResponse, "description": "Conflito de estado"},
    },
)
async def update_<feature>(
    <feature>_id: UUID,
    payload: Update<Feature>Request,
    service: Annotated[<Feature>Service, Depends(get_<feature>_service)],
) -> <Feature>Response:
    """Aplica um PATCH em campos não-nulos enviados pelo cliente."""
    return await service.update(<feature>_id, payload)


@router.delete(
    "/{<feature>_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um <feature>",
    responses={404: {"model": ErrorResponse, "description": "<Feature> não encontrado"}},
)
async def delete_<feature>(
    <feature>_id: UUID,
    service: Annotated[<Feature>Service, Depends(get_<feature>_service)],
) -> None:
    await service.delete(<feature>_id)
```

**Regras**:
- 1 endpoint = 1 handler. Não combinar verbos.
- **Tipo de retorno via annotation** (`-> <Feature>Response`), não `response_model=` no decorator — FastAPI ≥ 0.89 gera a mesma OpenAPI a partir da anotação e mantém a tipagem em um lugar só. Para listas: `-> list[<Feature>Response]`.
- `status_code=` explícito para `201` (created) e `204` (no content). Para `200` também é válido declarar explicitamente quando o endpoint tem `responses=` documentando erros, por consistência visual.
- `summary=` curto (≤ 60 chars) — vira o título do endpoint no Swagger.
- `description=` (ou docstring do handler) quando houver regra/efeito colateral que o consumidor precisa saber.
- `responses={404: ..., 409: ...}` para documentar erros esperados — os handlers globais já mapeiam os status; o `responses=` só ensina o Swagger que esses retornos existem.
- Nenhum `try/except` no controller — handlers globais cuidam.
- Nada de lógica de negócio aqui.

### 5. Router (`<entity>_router.py`)

Normalmente nada a fazer: o `<entity>_router.py` do módulo já agrega o `controllers/v1/<entity>_controller.py`, então o endpoint novo já está exposto via `/api/v1` (prefixo aplicado em `src/main.py`). Só mexer aqui se:
- Estiver dividindo a `v1` em múltiplos sub-controllers (ex.: `controllers/v1/<entity>_controller.py` + `controllers/v1/session_controller.py`) — adicionar mais um `router.include_router(...)`.
- Estiver introduzindo uma nova versão (`controllers/v2/`) — registrar lado-a-lado em `<entity>_router.py` e adicionar `app.include_router(<feature>_router, prefix="/api/v2")` em `main.py` (mantendo o v1 enquanto a depreciação acontece).

## Status codes (via DomainError)

Service lança, controller nunca captura; **sem `HTTPException`**. Status novo → nova subclasse de `DomainError` em `src/core/exceptions.py`. Regra completa: [conventions.md#erros](../../../docs/architecture/conventions.md#erros).

Mapa que vale para este fluxo (escolha a exceção certa ao implementar o método do service):

| Situação | Exceção | Status HTTP |
|---|---|---|
| Recurso não existe | `NotFoundError` | 404 |
| Conflito (ex: nome duplicado) | `ConflictError` | 409 |
| Regra de negócio violada | `ValidationError` | 422 |
| Sem autenticação válida | `UnauthorizedError` | 401 |
| Outro erro de domínio | `DomainError` (custom) | 400 (default) |

## Documentando erros no Swagger (`responses=`)

Handlers globais serializam o envelope, mas o `/docs` só mostra o **2xx** sem `responses=`. Passe `responses=` no decorator usando o `ErrorResponse` de `src/core/exceptions.py` (o mínimo por verbo está em [conventions.md#openapi](../../../docs/architecture/conventions.md#openapi)):

```python
@router.get(
    "/{order_id}",
    summary="Busca um pedido por ID",
    responses={
        404: {"model": ErrorResponse, "description": "Pedido não encontrado"},
    },
)
async def get_order(...) -> OrderResponse: ...
```

> Se `ErrorResponse` ainda não existir em `src/core/exceptions.py`, criar como `class ErrorResponse(BaseModel): error: ErrorDetail` espelhando o envelope dos handlers globais.

## Exemplos OpenAPI ricos

Para deixar o `/docs` útil, sempre passar `examples` e `description`:

```python
class CreateOrderRequest(BaseModel):
    customer_id: int = Field(
        ...,
        examples=[42],
        description="ID do cliente que está fazendo o pedido",
    )
    items: list[OrderItemRequest] = Field(
        ...,
        min_length=1,
        examples=[[{"product_id": 1, "quantity": 2}]],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": 42,
                "items": [{"product_id": 1, "quantity": 2}],
            },
        },
    )
```

## Verification

Atalhos `poe` para lint/type/test em [conventions.md#comandos](../../../docs/architecture/conventions.md#comandos).

1. **Lint/typing**: `uv run ruff check src/modules/<feature>/` e `uv run mypy src/modules/<feature>/` → limpos.
2. **App sobe sem erro**: `uv run uvicorn src.main:app --reload`.
3. **Aparece em `/docs`**: o endpoint novo está listado com `summary`, schema correto, exemplos, e a aba "Responses" mostra os status documentados em `responses=` (não só o 2xx).
4. **Smoke HTTP**: `curl` no novo endpoint retorna status correto (200, 201, 204) e corpo conforme a anotação de retorno.
5. **404 / 409 corretos**: para PATCH/DELETE em ID inexistente, retornar 404 com body `{"error": {"code": "NOT_FOUND", ...}}`.
6. **Testes**: criar via `pytest-unit` (mocking o repository) e/ou `pytest-integration` (HTTP completo). Não considerar a tarefa completa sem ao menos 1 teste unitário do path feliz e 1 do path de erro.

## Common pitfalls

- **HTTPException no controller** — sempre `DomainError` no service.
- **PATCH sem `exclude_unset=True`** — campos não enviados viram `null` e sobrescrevem dados do banco.
- **Repository retornando Pydantic** — repository devolve dict (do Prisma), service converte.
- **Reutilizar `<Feature>Response` como input de `POST`** — Request tem campos diferentes (sem `id`, `created_at`).
- **Sem anotação de retorno** — FastAPI serializa qualquer coisa que o service devolver, vazando campos internos. Sempre declarar `-> <Response>` (e `list[<Response>]` para listagens).
- **Misturar `response_model=` com return annotation** — escolher só um. Padrão do projeto: return annotation. `response_model=` permanece útil apenas quando o tipo serializado é diferente do tipo retornado pelo service (raro).
- **Esquecer `status_code=201` em POST de criação** — default é 200; convenção REST pede 201.
- **`DELETE` retornando body** — usar `status.HTTP_204_NO_CONTENT` e retornar `None`.
- **`responses=` ausente** — `/docs` mostra só o 2xx. Front não sabe que pode receber 404/409 e termina escrevendo tratamento por tentativa-e-erro.
- **`summary` longo ou ausente** — sem `summary`, o Swagger usa o nome da função (`update_<feature>`), que é técnico. Manter ≤ 60 chars descrevendo a ação no domínio.
- **Esquecer de adicionar o método no Protocol** — service vai falhar tipagem em `mypy` mesmo se a classe concreta tiver.

## Verification checklist (antes de entregar)

- [ ] Schema(s) novo(s) em `<entity>_schema.py` — Request e Response separados.
- [ ] Método novo no Protocol **e** na classe concreta do `<entity>_repository.py` (se acessa DB).
- [ ] Método novo no `<entity>_service.py` — sem importar Prisma, sem capturar exceções, levanta `DomainError`.
- [ ] Handler novo em `controllers/v1/<entity>_controller.py` — com `-> <Response>` (return annotation), `status_code` correto, `summary=`, e `responses=` cobrindo os erros esperados (mínimo 404 para `/{id}`, 409 quando houver conflito). Path do decorator é relativo (`""`, `"/{id}"`) — `/api/v1/<recurso>` é resolvido por `prefix` + `include_router`.
- [ ] Sem `try/except` no controller. Sem `HTTPException` em lugar nenhum.
- [ ] Naming HTTP REST-coerente.
- [ ] `ruff` e `mypy` limpos.
- [ ] Endpoint visível em `/docs` com `summary`, exemplos e a aba "Responses" listando 2xx + erros documentados.
- [ ] Pelo menos 1 teste unitário e 1 teste de erro 404/409 cobrindo o novo endpoint.
