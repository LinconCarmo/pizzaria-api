---
name: pydantic-schema
description: Cria schemas Pydantic v2 (Request/Response DTOs) em src/modules/<feature>/schema.py com validação, exemplos OpenAPI e separação clara entre input e output. Use quando o usuário pedir "criar schema X", "DTO de entrada/saída", "validação Pydantic para Y", "modelo de request/response", ou quando precisar adicionar/refatorar tipos em um schema existente.
---

# Pydantic Schema Skill

Use esta skill para criar ou modificar DTOs Pydantic v2 dentro de `src/modules/<feature>/schema.py`, seguindo as convenções do pizzaria-api.

> Referência arquitetural: [`docs/architecture/modular-monolith.md`](../../../docs/architecture/modular-monolith.md) (seção 4 — Schema). Decisão: [ADR 0001](../../../docs/adr/0001-adotar-modular-monolith-em-camadas.md).

## Quando usar

- "Crie o schema para criar produto"
- "DTO de input do endpoint X"
- "Adicionar validação de CPF no schema de cliente"
- "Refatorar o schema de pedido"
- "Quero retornar só id, nome e preço — preciso de um Response enxuto"

## Quando NÃO usar

- Criar módulo inteiro do zero → `create-module` (já gera o `schema.py` inicial).
- Schema vai em `src/shared/types.py` por ser cross-module → editar diretamente, esta skill é por feature.

## Princípios

### 1. Request e Response **sempre separados**

Nunca usar o mesmo modelo Pydantic para input e output. Um Request **nunca tem** `id`, `created_at`, `updated_at`; um Response **sempre tem**.

```python
# ❌ ERRADO
class Order(BaseModel):
    id: int | None = None
    customer_id: int
    created_at: datetime | None = None

# ✅ CORRETO
class CreateOrderRequest(BaseModel):
    customer_id: int

class OrderResponse(_BaseSchema):
    id: int
    customer_id: int
    created_at: datetime
```

### 2. Nunca expor o modelo Prisma cru

Mesmo que o Response tenha os mesmos campos do modelo Prisma, **sempre** definir um DTO Response explícito. Isso desacopla a API do schema do banco.

```python
# ❌ ERRADO
@router.get("/{id}")
async def get(id: int) -> dict:  # devolve resultado bruto do Prisma
    return await service.get(id)

# ✅ CORRETO
@router.get("/{id}", response_model=OrderResponse)
async def get(id: int) -> OrderResponse:
    return await service.get(id)
```

### 3. Naming

| Tipo | Padrão | Exemplo |
|---|---|---|
| Criação | `Create<Resource>Request` | `CreateOrderRequest` |
| Update parcial | `Update<Resource>Request` | `UpdateOrderRequest` |
| Update completo (PUT) | `Replace<Resource>Request` | `ReplaceOrderRequest` |
| Filtro de listagem | `<Resource>FilterRequest` ou `<Resource>Query` | `OrderFilterRequest` |
| Resposta completa | `<Resource>Response` | `OrderResponse` |
| Resposta resumida (listagens) | `<Resource>SummaryResponse` | `OrderSummaryResponse` |
| Sub-recurso/nested | `<Sub>Request` / `<Sub>Response` | `OrderItemRequest` |

Singular sempre (`OrderResponse`, não `OrdersResponse`). Listagens são `list[<Resource>Response]`.

### 4. Base config compartilhada

Para Responses que vêm de objetos com atributos (Prisma result), use `from_attributes=True`:

```python
from pydantic import BaseModel, ConfigDict


class _BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,      # aceita .id, .name (ORM result)
        populate_by_name=True,     # aceita createdAt OU created_at
        str_strip_whitespace=True, # tira espaços nas pontas de str
    )
```

> Se vários módulos repetem isso, mover para `src/shared/types.py` como `BaseSchema` exportado. Primeiro uso real → fazer essa extração.

Requests **não** precisam de `from_attributes`. Mantenha-os com `BaseModel` puro.

### 5. OpenAPI: `examples` por campo (não só no modelo)

Cada campo em `*Request` e `*Response` deve ter `Field(..., description=..., examples=[...])` quando fizer sentido documentar o campo no Swagger.

- `json_schema_extra` no `model_config` gera **um** exemplo de corpo inteiro — útil como complemento, **não** substitui `examples=` em cada `Field`.
- Preferir `examples=` por campo para que `/docs` mostre exemplos interativos campo a campo.

```python
# ✅ CORRETO — exemplos por campo
email: EmailStr = Field(
    ..., description="User email address", examples=["ana@example.com"]
)

# ⚠️ Insuficiente sozinho — só exemplo de corpo
model_config = ConfigDict(
    json_schema_extra={"examples": [{"email": "ana@example.com", "name": "Ana"}]},
)
```

## Templates

### Request — criação

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateOrderRequest(BaseModel):
    customer_id: int = Field(
        ...,
        gt=0,
        examples=[42],
        description="ID do cliente que está realizando o pedido",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        examples=["Sem cebola"],
        description="Observações livres",
    )
    items: list["CreateOrderItemRequest"] = Field(
        ...,
        min_length=1,
        description="Lista de itens do pedido (pelo menos 1)",
    )

    @field_validator("notes")
    @classmethod
    def empty_string_to_none(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            return None
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": 42,
                "notes": "Sem cebola",
                "items": [{"product_id": 1, "quantity": 2}],
            },
        },
    )
```

### Request — update parcial (PATCH)

Todos os campos opcionais com default `None`. Use `model_dump(exclude_unset=True)` no service.

```python
class UpdateOrderRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=500)
    status: OrderStatus | None = Field(default=None)
```

### Request — filtro de listagem (query params)

```python
class OrderFilterRequest(BaseModel):
    customer_id: int | None = None
    status: OrderStatus | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

No controller, receber como query params:

```python
@router.get("/", response_model=list[OrderSummaryResponse])
async def list_orders(
    filters: OrderFilterRequest = Depends(),
    service: OrderService = Depends(get_order_service),
) -> list[OrderSummaryResponse]:
    return await service.list(filters)
```

### Response — completa

```python
from datetime import datetime


class OrderResponse(_BaseSchema):
    id: int = Field(..., examples=[1])
    customer_id: int = Field(..., examples=[42])
    status: OrderStatus = Field(..., examples=[OrderStatus.PENDING])
    notes: str | None = Field(default=None, examples=["Sem cebola"])
    total: Decimal = Field(..., examples=["49.90"])
    items: list["OrderItemResponse"] = Field(default_factory=list)
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
```

> `alias` quando o Prisma devolve `createdAt` mas você quer expor `created_at` (ou vice-versa). Com `populate_by_name=True` ambos os nomes funcionam na desserialização.

### Response — resumida (listagens grandes)

```python
class OrderSummaryResponse(_BaseSchema):
    id: int
    customer_id: int
    status: OrderStatus
    total: Decimal
    created_at: datetime = Field(..., alias="createdAt")
```

## Validators

### Field-level

```python
from pydantic import field_validator


class CreateUserRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 chars")
        return v
```

### Model-level (validação cruzada)

```python
from pydantic import model_validator


class CreatePromotionRequest(BaseModel):
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def end_after_start(self) -> "CreatePromotionRequest":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self
```

> Validation errors viram `RequestValidationError` automaticamente — handler global em `src/main.py` traduz para HTTP 422 com payload `{"error": {"code": "VALIDATION_ERROR", "details": [...]}}`.

## Tipos comuns

| Caso | Tipo Python | Pydantic Field |
|---|---|---|
| ID auto-increment | `int` | `Field(..., gt=0)` |
| UUID | `UUID` (de `uuid`) | `Field(...)` |
| Dinheiro | `Decimal` (de `decimal`) | `Field(..., max_digits=10, decimal_places=2)` |
| Data | `date` | `Field(...)` |
| Datetime | `datetime` | `Field(...)` |
| Enum | classe `Enum` de `enum` | `Field(...)` |
| Email | `EmailStr` (de `pydantic`) | `Field(...)` |
| Telefone BR | `str` + validator com regex | `Field(..., pattern=r"^\+?55\d{10,11}$")` |
| CPF | `str` + validator (não usar `int` — perde zeros à esquerda) | validator dedicado |

> Para Money: **sempre `Decimal`**, nunca `float`. Float trunca centavos.

## Enums

Definir no próprio `schema.py` se for específico do módulo. Se for cross-module, em `src/shared/types.py`.

```python
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELED = "CANCELED"
```

Usar `str, Enum` (não `Enum` puro) para serialização limpa.

## Nested models

```python
from uuid import UUID


class CreateOrderItemRequest(BaseModel):
    product_id: UUID = Field(..., examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"])
    quantity: int = Field(..., ge=1, le=99)


class CreateOrderRequest(BaseModel):
    items: list[CreateOrderItemRequest] = Field(..., min_length=1)
```

> **IDs (PKs e FKs) são `uuid.UUID`** — ver [ADR 0003](../../../docs/adr/0003-ids-uuid.md). Pydantic valida formato automaticamente; o Swagger expõe como `string($uuid)`.

Pydantic v2 resolve forward references — se houver ciclo, usar string (`"CreateOrderItemRequest"`) e chamar `model_rebuild()` no final do módulo.

## Não expor

Nunca colocar em Response:
- Hash de senha (`password_hash`)
- Tokens (`access_token`, `refresh_token` — exceto no endpoint de login)
- Campos internos de auditoria que não interessam ao cliente (`internal_notes`, `migration_marker`)
- IDs externos sensíveis (Stripe customer_id, etc.)

Quando o Response viria do Prisma com esses campos, **mapear explicitamente** no service:

```python
async def get(self, id: int) -> OrderResponse:
    raw = await self._repository.find_by_id(id)
    return OrderResponse.model_validate({
        "id": raw["id"],
        "customer_id": raw["customer_id"],
        # password_hash do raw NÃO é incluído
    })
```

## Verification

1. `uv run ruff check src/modules/<feature>/schema.py` → 0 erros.
2. `uv run mypy src/modules/<feature>/schema.py` → 0 erros.
3. Abrir `/docs` e conferir:
   - Schema aparece com nome correto.
   - Campos têm `description` e `examples` visíveis.
   - Validações (min/max, regex) estão refletidas no schema OpenAPI.
4. Smoke de validação:
   - Enviar payload válido → 200/201.
   - Enviar payload com regra violada → 422 com `{"error": {"code": "VALIDATION_ERROR", "details": [...]}}`.

## Common pitfalls

- **Mesmo modelo para Request e Response** — quebra encapsulamento, vaza `id`/`created_at` para criação, força campos opcionais que deveriam ser obrigatórios.
- **`Optional[X]` em vez de `X | None`** — projeto usa Python 3.13, sintaxe moderna `X | None` é preferida.
- **`float` para dinheiro** — usar `Decimal`.
- **Sem `examples`/`description` em `Field`** — `/docs` fica pobre; `json_schema_extra` sozinho não documenta campo a campo.
- **Só `json_schema_extra` sem `examples=` por campo** — integradores veem um corpo de exemplo, mas não exemplos por propriedade no schema.
- **`alias` sem `populate_by_name=True`** — Pydantic aceita só o alias, perde compatibilidade com nome snake_case.
- **Validator lança `HTTPException`** — lançar `ValueError`; Pydantic transforma em `RequestValidationError`, handler global converte para 422.
- **Expor `password_hash` em Response** — risco de segurança. Sempre mapear campos explícitos.
- **`from_attributes` em Request** — Request vem de JSON, não de ORM. Não precisa.
- **`*Response` sem `_BaseSchema`** — perde `from_attributes`, `model_validate(prisma_result)` falha.

## Verification checklist (antes de entregar)

- [ ] Request e Response separados, com nomes seguindo a convenção (`Create<R>Request`, `<R>Response`).
- [ ] Response herda de `_BaseSchema` (ou equivalente com `from_attributes=True`).
- [ ] Todo `Field` tem `description` e (quando faz sentido) `examples` — não depender só de `json_schema_extra` no `model_config`.
- [ ] Money é `Decimal`, IDs auto-increment são `int` com `gt=0`.
- [ ] Validators usam `ValueError`, nunca `HTTPException`.
- [ ] Nenhum campo sensível (`password_hash`, tokens internos) no Response.
- [ ] `ruff` e `mypy` limpos.
- [ ] `/docs` mostra o schema com exemplos.
