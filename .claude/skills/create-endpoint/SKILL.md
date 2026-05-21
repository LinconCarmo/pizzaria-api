---
name: create-endpoint
description: Adiciona um endpoint a um módulo existente em src/modules/<feature>/ — rota no controller, método no service, schemas Request/Response, e (se necessário) método no repository. Use quando o módulo já existe e o usuário pedir "adicionar endpoint X", "criar rota Y", "novo método na feature Z", "expor operação W via HTTP".
---

# Create Endpoint Skill

Use esta skill quando o módulo **já existe** em `src/modules/<feature>/` e você precisa adicionar mais uma operação HTTP. Para criar um módulo do zero, use a skill `create-module`.

> Referência arquitetural: [`docs/architecture/modular-monolith.md`](../../../docs/architecture/modular-monolith.md) (seções 4 e 6). Decisão: [ADR 0001](../../../docs/adr/0001-adotar-modular-monolith-em-camadas.md).

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

1. **Módulo existe**: `ls src/modules/<feature>/controller.py` deve achar o arquivo.
2. **Operação suportada pelo modelo Prisma**: confirmar que `schema.prisma` tem os campos/relações necessários.
3. **REST coerente**: a nova rota segue o REST plural do módulo?
   - `GET /<features>/` — listagem
   - `POST /<features>/` — criação
   - `GET /<features>/{id}` — detalhe
   - `PATCH /<features>/{id}` — update parcial
   - `DELETE /<features>/{id}` — remoção
   - `POST /<features>/{id}/<action>` — sub-recurso/ação (cancel, approve, ship)
4. **Idempotência**: operações `PUT` e `DELETE` devem ser idempotentes; `POST` cria.

## Fluxo de implementação (bottom-up)

Implemente nesta ordem para manter cada camada tipada e testável de baixo pra cima:

### 1. Schema (`schema.py`)

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

**Regras**:
- `*Request` para input, `*Response` para output. Nunca o mesmo modelo.
- Para `PATCH`, todos os campos opcionais.
- Para listagens grandes, considerar `*SummaryResponse` (subset).
- Sempre adicionar `examples=[...]` em `Field` para enriquecer o `/docs`.

> Use a skill `pydantic-schema` se a validação for não-trivial (validators, regex, restrições cruzadas).

### 2. Repository (`repository.py`)

Se a operação precisa de acesso a dados não coberto, adicionar **tanto no Protocol quanto na classe**:

```python
class <Feature>RepositoryProtocol(Protocol):
    # ... existentes ...
    async def update(self, <feature>_id: int, data: dict) -> dict | None: ...
    async def delete(self, <feature>_id: int) -> None: ...


class <Feature>Repository:
    # ... existentes ...
    async def update(self, <feature>_id: int, data: dict) -> dict | None:
        return await self._db.<feature>.update(
            where={"id": <feature>_id},
            data=data,
        )

    async def delete(self, <feature>_id: int) -> None:
        await self._db.<feature>.delete(where={"id": <feature>_id})
```

**Regras**:
- Métodos do repository retornam dicts (resultado bruto do Prisma) ou `None`. **Não retornam Pydantic** — quem converte é o service.
- Não embutir regra de negócio. Repository é I/O puro.
- Se a query precisa de joins/relations, adicionar `include={"items": True}` no Prisma call.

### 3. Service (`service.py`)

Adicionar o método com regra de negócio:

```python
from src.core.exceptions import NotFoundError


class <Feature>Service:
    # ... existentes ...

    async def update(
        self,
        <feature>_id: int,
        data: Update<Feature>Request,
    ) -> <Feature>Response:
        patch = data.model_dump(exclude_unset=True)

        if not patch:
            return await self.get_by_id(<feature>_id)

        entity = await self._repository.update(<feature>_id, patch)

        if entity is None:
            raise NotFoundError(f"<Feature> {<feature>_id} not found")

        return <Feature>Response.model_validate(entity)

    async def delete(self, <feature>_id: int) -> None:
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

### 4. Controller (`controller.py`)

Adicionar o handler:

```python
from fastapi import status


@router.patch("/{<feature>_id}", response_model=<Feature>Response)
async def update_<feature>(
    <feature>_id: int,
    payload: Update<Feature>Request,
    service: <Feature>Service = Depends(get_<feature>_service),
) -> <Feature>Response:
    return await service.update(<feature>_id, payload)


@router.delete("/{<feature>_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_<feature>(
    <feature>_id: int,
    service: <Feature>Service = Depends(get_<feature>_service),
) -> None:
    await service.delete(<feature>_id)
```

**Regras**:
- 1 endpoint = 1 handler. Não combinar verbos.
- `response_model=...` sempre que retornar payload (inclusive listas: `list[<Feature>Response]`).
- `status_code=` explícito para `201` (created) e `204` (no content).
- Nenhum `try/except` no controller — handlers globais cuidam.
- Nada de lógica de negócio aqui.

### 5. Router (`router.py`)

Normalmente nada a fazer: o `router.py` agrega o `controller.py`, então o endpoint novo já está exposto. Só mexer aqui se:
- Estiver dividindo o controller em múltiplos sub-controllers.
- Estiver adicionando sub-router para uma área (ex.: `/orders/{id}/items` em controller separado).

## Status codes (via DomainError)

Mapeamento já feito em `src/core/exceptions.py` — não precisa repetir no controller:

| Situação | Exceção | Status HTTP |
|---|---|---|
| Recurso não existe | `NotFoundError` | 404 |
| Conflito (ex: nome duplicado) | `ConflictError` | 409 |
| Regra de negócio violada | `ValidationError` | 422 |
| Sem autenticação válida | `UnauthorizedError` | 401 |
| Outro erro de domínio | `DomainError` (custom) | 400 (default) |

Se precisar de um código diferente, criar nova subclasse em `src/core/exceptions.py` herdando de `DomainError`.

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

1. **Lint/typing**: `uv run ruff check src/modules/<feature>/` e `uv run mypy src/modules/<feature>/` → limpos.
2. **App sobe sem erro**: `uv run uvicorn src.main:app --reload`.
3. **Aparece em `/docs`**: o endpoint novo está listado com schema correto e exemplos.
4. **Smoke HTTP**: `curl` no novo endpoint retorna status correto (200, 201, 204) e corpo conforme `response_model`.
5. **404 / 409 corretos**: para PATCH/DELETE em ID inexistente, retornar 404 com body `{"error": {"code": "NOT_FOUND", ...}}`.
6. **Testes**: criar via `pytest-unit` (mocking o repository) e/ou `pytest-integration` (HTTP completo). Não considerar a tarefa completa sem ao menos 1 teste unitário do path feliz e 1 do path de erro.

## Common pitfalls

- **HTTPException no controller** — sempre `DomainError` no service.
- **PATCH sem `exclude_unset=True`** — campos não enviados viram `null` e sobrescrevem dados do banco.
- **Repository retornando Pydantic** — repository devolve dict (do Prisma), service converte.
- **Reutilizar `<Feature>Response` como input de `POST`** — Request tem campos diferentes (sem `id`, `created_at`).
- **Sem `response_model`** — FastAPI serializa qualquer coisa que o service devolver, vazando campos internos. Sempre declarar.
- **Esquecer `status_code=201` em POST de criação** — default é 200; convenção REST pede 201.
- **`DELETE` retornando body** — usar `status.HTTP_204_NO_CONTENT` e retornar `None`.
- **Esquecer de adicionar o método no Protocol** — service vai falhar tipagem em `mypy` mesmo se a classe concreta tiver.

## Verification checklist (antes de entregar)

- [ ] Schema(s) novo(s) em `schema.py` — Request e Response separados.
- [ ] Método novo no Protocol **e** na classe concreta do `repository.py` (se acessa DB).
- [ ] Método novo no `service.py` — sem importar Prisma, sem capturar exceções, levanta `DomainError`.
- [ ] Handler novo no `controller.py` — com `response_model` e `status_code` corretos.
- [ ] Sem `try/except` no controller. Sem `HTTPException` em lugar nenhum.
- [ ] Naming HTTP REST-coerente.
- [ ] `ruff` e `mypy` limpos.
- [ ] Endpoint visível em `/docs` com exemplos.
- [ ] Pelo menos 1 teste unitário e 1 teste de erro 404/409 cobrindo o novo endpoint.
