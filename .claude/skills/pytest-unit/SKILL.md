---
name: pytest-unit
description: Cria testes unitários com pytest no pizzaria-api seguindo AAA, mocks tipados via spec, sem hit no banco/HTTP/Redis/RabbitMQ. Use quando o usuário pedir "criar testes unitários para service/repository/utility/schema X", "unit tests for Y", ou quando o subject under test pode ser exercitado sem dependências externas reais.
---

# Pytest Unit Test Skill

Use esta skill para criar testes **unitários** (sem I/O externo) com pytest no pizzaria-api. Para testes que precisam do banco real, use a skill `pytest-integration`.

> Referência — regras normativas: [conventions.md#testes](../../../docs/architecture/conventions.md#testes). Detalhe: [modular-monolith.md](../../../docs/architecture/modular-monolith.md) (seção 10 — Testes). Decisões: [ADRs](../../../docs/adr/).

## Quando usar

- "Crie testes unitários para `OrderService`"
- "Unit tests pro repository de produtos"
- "Testes do validator do `CreateOrderRequest`"
- "Cobertura unitária de `<algum método>`"
- Qualquer caso em que o SUT (subject under test) pode ser exercitado mockando seus colaboradores.

## Quando NÃO usar

- Precisa de banco real (constraints, transactions, generated columns) → `pytest-integration`.
- Precisa testar middleware/handler global no contexto do app real → `pytest-integration` com `httpx.AsyncClient`.
- Pure data fixture sem assertion → não é teste, é mock builder.

## Pre-flight checklist

Antes de escrever os testes, garantir:

1. **Dependências instaladas**:
   - `pytest` (já está em `pyproject.toml`)
   - `pytest-asyncio` para testes `async`
   - `pytest-mock` (opcional, mas recomendado) para `mocker` fixture

   Se faltar `pytest-asyncio`, executar:
   ```bash
   uv add --dev pytest-asyncio
   ```

2. **`pytest.ini` configurado**:
   ```ini
   [pytest]
   pythonpath = .
   asyncio_mode = auto
   ```
   Se `asyncio_mode = auto` não estiver, ou bater `@pytest.mark.asyncio` em cada teste async, ou adicionar essa linha.

3. **Diretório de unit tests**: `test/unit/` deve existir e espelhar `src/`. Se não existir, criar.

4. **SUT é unit-testável**: dependências externas (Prisma, HTTP, Redis, RabbitMQ) devem ser injetadas — não importadas globalmente. Se o SUT importa `prisma` direto, refatorar primeiro (a skill `create-module` já gera no padrão correto).

## File placement e naming

Naming/espelhamento de path são normativos ([#testes](../../../docs/architecture/conventions.md#testes)): teste em `test/unit/<mirror>/test_<entity>_<layer>.py`, espelhando caminho e nome do source. Mapa concreto:

  | Source | Teste |
  |---|---|
  | `src/modules/orders/order_service.py` | `test/unit/modules/orders/test_order_service.py` |
  | `src/modules/orders/order_repository.py` | `test/unit/modules/orders/test_order_repository.py` |
  | `src/core/exceptions.py` | `test/unit/core/test_exceptions.py` |
  | `src/shared/utils.py` | `test/unit/shared/test_utils.py` |

- **Filename**: prefixo `test_` (exigência do pytest), sem `_unit_`/`_spec_`.
- **Um arquivo de teste por arquivo de source**. Múltiplos `class TestX:` se for útil agrupar.

## Estrutura obrigatória de cada teste

### 1. Imports (em ordem)

```python
# stdlib
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

# third-party
import pytest

# local — SUT e tipos
from src.core.exceptions import NotFoundError
from src.modules.orders.order_repository import OrderRepositoryProtocol
from src.modules.orders.order_schema import CreateOrderRequest, OrderResponse
from src.modules.orders.order_service import OrderService
```

### 2. Constantes hoisted (sem magic values)

IDs são `uuid.UUID` ([#uuid](../../../docs/architecture/conventions.md#uuid)). Para legibilidade, hoistar UUIDs determinísticos no topo do arquivo de teste — preferir `0000...-0001`, `0000...-0042` etc. para preservar a referência mental do "id 1, id 42" sem perder a tipagem forte.

```python
from uuid import UUID

ORDER_ID = UUID("00000000-0000-4000-8000-000000000001")
NON_EXISTENT_ID = UUID("00000000-0000-4000-8000-0000000000ff")
CUSTOMER_ID = UUID("00000000-0000-4000-8000-000000000042")
DEFAULT_PRICE = Decimal("49.90")
```

Para casos onde o ID é só "qualquer um" (ex.: gerar 20 entidades distintas), usar `uuid4()` direto — sem precisar de determinismo.

### 3. Fixtures e factories

**Dados de domínio (rows Prisma, DTOs Pydantic) vêm de `test/factories/<entity>_factory.py`** — nunca redefinir helpers locais `_raw_*`, `_user_response`, `_make_<entity>` quando a factory existe (regra: [#testes](../../../docs/architecture/conventions.md#testes)).

```python
from test.factories.order_factory import make_order_row, make_create_order_request
```

Fixtures locais ficam reservadas para **wiring de SUT + mocks** (não-dados):

```python
@pytest.fixture
def order_repository() -> MagicMock:
    return MagicMock(spec=OrderRepositoryProtocol)


@pytest.fixture
def order_service(order_repository: MagicMock) -> OrderService:
    return OrderService(order_repository)
```

Para dados, chame a factory direto no Arrange (passando `**overrides`):

```python
order_repository.find_by_id = AsyncMock(return_value=make_order_row(id=ORDER_ID))
```

Se quiser, encapsule a chamada em fixture — mas só se houver reuso real entre testes do arquivo:

```python
@pytest.fixture
def order_row() -> SimpleNamespace:
    return make_order_row()
```

> **Sempre `spec=<Protocol|Class>`** ([#testes](../../../docs/architecture/conventions.md#testes)): mock sem `spec` aceita qualquer atributo e dá falso-positivo quando o código chama método inexistente.

### 4. Testes (AAA)

```python
class TestOrderService:
    class TestGetById:
        async def test_returns_response_when_order_exists(
            self,
            order_service: OrderService,
            order_repository: MagicMock,
            order_row: dict,
        ) -> None:
            order_repository.find_by_id = AsyncMock(return_value=order_row)

            result = await order_service.get_by_id(ORDER_ID)

            assert result.id == ORDER_ID
            assert result.customer_id == CUSTOMER_ID
            order_repository.find_by_id.assert_awaited_once_with(ORDER_ID)

        async def test_raises_not_found_when_order_missing(
            self,
            order_service: OrderService,
            order_repository: MagicMock,
        ) -> None:
            order_repository.find_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError, match="Order"):
                await order_service.get_by_id(NON_EXISTENT_ID)

            order_repository.find_by_id.assert_awaited_once_with(NON_EXISTENT_ID)
```

**AAA e naming** (`test_<verb>_<expected>_when_<condition>`, blocos separados por linha em branco, `test_*` ≤ ~15 linhas) são normativos — ver [#testes](../../../docs/architecture/conventions.md#testes). Aqui o Act chama o SUT (1 linha quando possível) e o Assert verifica resultado **e** interações; se estourar 15 linhas, extrair builder de fixture.

## Mocks tipados

### Repository (via Protocol)

```python
from unittest.mock import MagicMock

from src.modules.orders.order_repository import OrderRepositoryProtocol
from test.factories.order_factory import make_order_row


repository = MagicMock(spec=OrderRepositoryProtocol)
repository.find_by_id = AsyncMock(return_value=make_order_row())
```

DTOs Pydantic no Arrange também vêm da factory — não instanciar `CreateOrderRequest(...)` inline com payload "feliz":

```python
from test.factories.order_factory import make_create_order_request

data = make_create_order_request(customer_id=42)
result = await service.create(data)
```

### Service async

```python
from unittest.mock import AsyncMock

service_mock = AsyncMock(spec=OrderService)
service_mock.create.return_value = expected_response
```

### Funções externas / utilitários

```python
from unittest.mock import patch

@patch("src.shared.utils.send_event")
async def test_publishes_event(send_event_mock, ...):
    ...
```

> Prefira injeção sobre `patch`. Use `patch` só quando o módulo importa funções diretamente (sem DI).

### Prisma — **NÃO** mockar Prisma diretamente em unit tests

Repository é unit-testável **se** for testado contra a sua própria interface. Para testar lógica que envolve Prisma de verdade, vá para `pytest-integration`.

Exemplo aceitável: testar que o repository chama o método correto do client Prisma mockado:

```python
@pytest.fixture
def prisma_mock() -> MagicMock:
    prisma = MagicMock()
    prisma.order = MagicMock()
    prisma.order.find_unique = AsyncMock()
    return prisma


async def test_find_by_id_calls_prisma_correctly(prisma_mock: MagicMock) -> None:
    prisma_mock.order.find_unique.return_value = order_row
    repo = OrderRepository(prisma_mock)

    result = await repo.find_by_id(ORDER_ID)

    prisma_mock.order.find_unique.assert_awaited_once_with(where={"id": ORDER_ID})
    assert result == order_row
```

Use esse padrão com moderação. Para garantir que o `where` clause realmente bate no banco, `pytest-integration` é mais valioso.

## Cobertura mínima por tipo de SUT

| SUT | Mínimo |
|---|---|
| **Service** | 1 path feliz por método público + 1 por exceção que o método pode levantar (`NotFoundError`, `ConflictError`, ...) |
| **Repository** (interface contract) | 1 happy + 1 not-found (`return None`), assertions em `assert_awaited_once_with` |
| **Schema/DTO** | 1 payload válido + 1 falha por regra de validação (`min_length`, regex, validator custom, `model_validator`) |
| **Utility** | 1 por branch observável |
| **Exception** | já coberto em `test/test_exceptions.py`; só adicionar caso adicione subclasse |

## Validação de schemas Pydantic

Duas opções equivalentes — escolher a mais legível:

### A — direto

```python
import pytest
from pydantic import ValidationError

from src.modules.orders.order_schema import CreateOrderRequest


def test_create_order_request_rejects_empty_items() -> None:
    with pytest.raises(ValidationError) as exc:
        CreateOrderRequest(customer_id=1, items=[])

    errors = exc.value.errors()
    assert any(e["loc"] == ("items",) for e in errors)
```

### B — via `model_validate` com payload dict

```python
def test_create_order_request_accepts_valid_payload() -> None:
    payload = {"customer_id": 1, "items": [{"product_id": 1, "quantity": 2}]}

    dto = CreateOrderRequest.model_validate(payload)

    assert dto.customer_id == 1
    assert len(dto.items) == 1
```

## Async tests

Com `asyncio_mode = auto` em `pytest.ini`, funções `async def` são automaticamente reconhecidas. Caso contrário:

```python
@pytest.mark.asyncio
async def test_something() -> None:
    ...
```

**Não usar `asyncio.run`** dentro de testes — deixa pytest-asyncio gerenciar o loop.

## Typing discipline

`Any` é banido ([#tipos](../../../docs/architecture/conventions.md#tipos)) e mocks tipados/`spec=` são normativos ([#testes](../../../docs/architecture/conventions.md#testes)). Específico desta skill:

- Anotar tipos de fixtures (`-> MagicMock`, `-> OrderService`); `cast(OrderRepositoryProtocol, mock)` quando mypy reclamar.
- **`AsyncMock` para coroutines**, `MagicMock` para sync. Métodos individuais async em um `MagicMock(spec=...)`: atribuir `mock.method = AsyncMock(...)`.

## Gates antes de entregar

Executar em ordem:

1. **Ruff**: `uv run ruff check test/unit/` → 0 erros.
2. **Mypy** (opcional para testes, mas recomendado): `uv run mypy test/unit/`.
3. **Pytest**: `uv run pytest test/unit/ -v` → todos verdes.
4. **Cobertura** (opcional): `uv run poe test-cov` ou `uv run pytest --cov=src --cov-report=term-missing` — checar que o SUT está coberto.

## Common pitfalls

- **`MagicMock()` sem `spec`** — aceita qualquer chamada, esconde refactor breakage. Sempre `MagicMock(spec=ClasseOuProtocol)`.
- **Async method em `MagicMock`** retorna coroutine `MagicMock` (não awaitable). Use `mock.method = AsyncMock(...)` ou `MagicMock(spec=AsyncClass)` para sync wrappers.
- **`patch` em vez de injetar** — se o código permite DI (e o nosso permite, via FastAPI Depends), prefira injetar.
- **`assert_called_once` vs `assert_awaited_once`** — coroutines usam `assert_awaited_once_with`. Trocar dá falso-positivo (passa mesmo quando não foi awaited).
- **Esquecer `await`** no Act → o teste passa mas não testa o que deveria.
- **Magic values duplicados** — IDs, strings de erro repetidos. Hoist para constantes no topo.
- **Mock retornando objeto Pydantic em `find_*`** — repository retorna dict (Prisma result), não Pydantic. Manter o mock fiel ao contrato real.
- **`asyncio.run(...)` dentro de teste** — quebra pytest-asyncio. Use `async def` + auto-mode.
- **Testar implementação vs comportamento** — focar em "dado input X, service retorna Y / lança Z". Evitar verificar a ordem exata de chamadas internas a menos que faça parte do contrato.
- **Helper local `_raw_*` / `_make_<entity>` duplicando factory existente** — toda entidade de domínio tem (ou deve ter) factory em `test/factories/<entity>_factory.py`. Importar do barrel `from test.factories import make_<entity>_*` em vez de redefinir.

## Verification checklist (antes de entregar)

- [ ] Arquivo em `test/unit/<mirror>/test_<entity>_<layer>.py`, espelhando `src/`.
- [ ] `class TestX` agrupando, `class TestX.TestMethod` para sub-grupos por método.
- [ ] Toda fixture e mock tem tipo anotado e usa `spec=`.
- [ ] Mocks/DTOs de entidades de domínio criados via factory (`test/factories/<entity>_factory.py`), não helpers locais `_raw_*`/`_make_<entity>`.
- [ ] AAA com linhas em branco; cada `test_*` ≤ 15 linhas.
- [ ] Magic values hoisted como constantes no topo.
- [ ] Nenhum `Any`; nenhum `Mock()` sem `spec`; nenhum `patch` substituível por injeção.
- [ ] Async: `await` no Act; `assert_awaited_once_with` nos asserts; `asyncio_mode = auto` ou `@pytest.mark.asyncio`.
- [ ] Cobertura: ≥ 1 path feliz + ≥ 1 path de erro por método público do SUT.
- [ ] `ruff check` e `pytest` verdes.
