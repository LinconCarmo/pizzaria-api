---
name: pytest-integration
description: Cria testes de integração usando httpx.AsyncClient + Prisma real (MySQL via docker-compose), exercitando o pipeline HTTP completo do FastAPI no pizzaria-api. Use quando o teste precisa do banco de verdade — constraints, transactions, generated columns, migrations — ou quando o usuário pedir "criar testes de integração", "e2e tests", "testar endpoint X end-to-end".
---

# Pytest Integration Test Skill

Use esta skill para testes que exercitam o pipeline HTTP completo (FastAPI + Pydantic + Service + Repository + Prisma + MySQL real). Para testes que só validam lógica de Service/Repository com mocks, use `pytest-unit`.

> Referência arquitetural: [`docs/architecture/modular-monolith.md`](../../../docs/architecture/modular-monolith.md) (seção 9 — Testes). Decisão: [ADR 0001](../../../docs/adr/0001-adotar-modular-monolith-em-camadas.md).

## Quando usar

- "Testar `POST /orders` end-to-end"
- "Garantir que o constraint UNIQUE de email funciona"
- "Validar que a transaction faz rollback se algum passo falhar"
- "Testar comportamento real do Prisma (`P2003`, `P2025`)"
- "E2E test do fluxo de criação de pedido"
- Qualquer teste em que o valor está em **executar o pipeline real**, não mockar.

## Quando NÃO usar

- Testar regra de negócio isolada de service → `pytest-unit` (mais rápido, sem flakiness).
- Validar Pydantic schema → `pytest-unit`.
- Smoke manual (curl) → não é teste automatizado; rodar `uv run poe start-dev` e usar `/docs`.

## Pre-flight checklist

1. **Dependências instaladas**:
   ```bash
   uv add --dev pytest-asyncio httpx
   ```
   `httpx` é necessário para `AsyncClient`. `pytest-asyncio` para suporte async.

2. **`pytest.ini`** (ou bloco `[tool.pytest.ini_options]` no `pyproject.toml`):
   ```ini
   [pytest]
   pythonpath = .
   asyncio_mode = auto
   markers =
       integration: tests que precisam de MySQL real (rodar com `pytest -m integration`)
   ```

3. **Infra subida**:
   ```bash
   docker compose up -d mysql
   uv run prisma migrate dev --schema=src/infra/prisma/schema.prisma
   uv run prisma generate --schema=src/infra/prisma/schema.prisma
   ```

4. **Banco de teste isolado**: integration tests **não devem** rodar contra o MySQL de desenvolvimento. Duas opções:
   - **Recomendado**: variável `DATABASE_URL_TEST` apontando para outro schema (`pizzaria_test`). Override via fixture.
   - Alternativa: rodar `prisma migrate reset` antes da suíte (destrói dados — não usar contra dev).

   Se o `.env.example` ainda não tem `DATABASE_URL_TEST`, adicionar antes de criar testes que escrevem.

5. **Diretório**: `test/integration/` deve existir e espelhar `src/`. Criar se não existir.

## File placement e naming

- **Path**: `test/integration/<mirror>/test_<basename>.py`.

  | Source | Teste de integração |
  |---|---|
  | `src/modules/orders/controller.py` | `test/integration/modules/orders/test_controller.py` |
  | `src/modules/users/repository.py` | `test/integration/modules/users/test_repository.py` |

- **Filename**: `test_<basename>.py` — mesmo prefixo dos unit tests, mas em diretório separado para rodar isoladamente (`pytest test/integration` vs `pytest test/unit`).

- **Marker**: cada teste decorado com `@pytest.mark.integration` (permite excluir do CI rápido com `pytest -m "not integration"`).

## Conftest base (uma vez por suíte)

Criar `test/integration/conftest.py`:

```python
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from prisma import Prisma

from src.main import app


@pytest.fixture(scope="session")
async def db() -> AsyncIterator[Prisma]:
    client = Prisma()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture(scope="session")
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
async def clean_database(db: Prisma) -> AsyncIterator[None]:
    yield
    # cleanup determinístico — apaga em ordem reversa de FK
    await db.orderitem.delete_many()
    await db.order.delete_many()
    await db.product.delete_many()
    await db.user.delete_many()
```

> Adicione `delete_many()` para cada tabela conforme o `schema.prisma` evolui. Mantenha a **ordem reversa de FK** para não violar constraints.

> Para suítes grandes, considerar truncar via SQL raw (`db.execute_raw("TRUNCATE ...")`) — mais rápido que `delete_many`.

## Estrutura de um teste

### 1. Imports

```python
import pytest
from httpx import AsyncClient
from prisma import Prisma
```

### 2. Marker + factories de seed

Seeds que escrevem direto no banco vêm de `test/factories/<feature>.py` (mesmo barrel usado pelos unit tests). Nada de `_seed_*` local quando já existe `seed_<entity>`.

```python
pytestmark = pytest.mark.integration

from test.factories.users import seed_user
# Para builders de payload HTTP, importe também o DTO factory:
from test.factories.users import make_create_user_request
```

Assinatura padrão da factory de seed: `async def seed_<entity>(db: Prisma, *, <defaults>, **overrides) -> <PrismaModel>`. Ver §9 do `modular-monolith.md` para a regra geral.

### 3. Testes — AAA com banco real

```python
class TestCreateOrder:
    async def test_returns_201_with_created_order(
        self,
        client: AsyncClient,
        db: Prisma,
    ) -> None:
        user = await seed_user(db)

        response = await client.post(
            "/orders/",
            json={"customer_id": user.id, "items": [{"product_id": 1, "quantity": 2}]},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["customer_id"] == user.id
        assert body["id"] > 0

        persisted = await db.order.find_unique(where={"id": body["id"]})
        assert persisted is not None
        assert persisted.customer_id == user.id

    async def test_returns_404_when_customer_missing(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/orders/",
            json={"customer_id": 99999, "items": [{"product_id": 1, "quantity": 1}]},
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
```

### 4. Cobertura por endpoint

Para cada endpoint novo, no mínimo:

- **Path feliz**: status correto (200/201/204) + body conforme `response_model` + estado persistido conferido lendo o DB.
- **404 / 409 / 422**: condição de erro retorna status e payload `{"error": {"code": ..., "message": ..., "details": ...}}` corretos.
- **Validação de borda**: campos obrigatórios faltando → 422.
- **Idempotência (se aplicável)**: PUT/DELETE chamado duas vezes não muda o estado.

## Convenções

- **AAA preservado** mesmo com banco real. Seeds = Arrange; chamada HTTP = Act; assertions HTTP + DB = Assert.
- **Sem `time.sleep` ou retry**. Se o teste é flaky, o problema é design (timing real do banco, locks). Investigar, não disfarçar.
- **Sem ordem entre testes**. `clean_database` autouse garante estado limpo. Não escrever testes que dependem de ordem de execução.
- **Não compartilhar state entre testes via fixture session-scoped**, exceto `client` e `db`. Dados → fixture function-scoped + cleanup.
- **Asserts em ambos os lados**: HTTP response **e** estado do banco. Só HTTP não prova que persistiu.

## Constantes / fixtures comuns

```python
DEFAULT_EMAIL = "user@example.com"
NON_EXISTENT_ID = 99999
```

Builders de **dados** (seed no DB, payloads para HTTP) **sempre** ficam em `test/factories/<feature>.py` — mesmo barrel usado pelos unit tests, importar via `from test.factories import seed_<entity>, make_create_<entity>_request`. Helpers que orquestram HTTP (ex: `_create_user_via_http(client, **overrides)` que faz POST + assert 201) podem ficar locais no arquivo de teste — eles não são factory de dado.

## Async

`asyncio_mode = auto` faz pytest descobrir `async def` automaticamente. Fixtures async também são descobertas. Caso contrário, decorar com `@pytest.mark.asyncio`.

## Performance

Integration tests são **lentos por design** (banco real). Mitigações:

- **Não use** integration test quando unit test serve. Regra: se você está mockando 80% do colaboradores, isso era pra ser unit.
- **Reutilize `db` e `client` em escopo session** (já está no conftest).
- **`TRUNCATE` em vez de `delete_many` em loop** para suítes grandes (centenas de testes).
- **Paralelização** com `pytest-xdist` exige bancos isolados por worker (`pizzaria_test_gw0`, `pizzaria_test_gw1`) — só configurar quando a suíte estiver pesada.

## Gates antes de entregar

1. **Ruff**: `uv run ruff check test/integration/` → 0 erros.
2. **Banco subido**: `docker ps | grep mysql` mostra container saudável.
3. **Migrations aplicadas**: `uv run prisma migrate status --schema=src/infra/prisma/schema.prisma` limpo.
4. **Testes verdes**: `uv run pytest test/integration -v -m integration` → todos passam.
5. **Sem flakiness**: rodar 3x seguidas — se 1 falha intermitente, **bloqueia entrega**.

## Common pitfalls

- **Vazamento de dados entre testes** — esquecer `clean_database` autouse ou ordem errada de `delete_many` (viola FK).
- **Banco de dev sendo apagado** — testes rodando contra `DATABASE_URL` de desenvolvimento. Configurar `DATABASE_URL_TEST` separado e override no conftest.
- **`HTTPException` esperado em vez de payload `DomainError`** — handlers globais retornam `{"error": {"code": "...", "message": "...", "details": ...}}`. Asserções devem bater nesse shape.
- **`pytest.mark.asyncio` faltando** quando `asyncio_mode = auto` não está configurado — teste é coletado mas não roda como coroutine (pytest avisa).
- **`time.sleep`** para esperar "consistência" do banco — Prisma é síncrono na transação; se você precisa esperar, está testando algo errado.
- **Assertar só status code** — sem checar body nem estado do banco, o teste passa mesmo quando o handler retorna 201 sem persistir.
- **Fixture `db` function-scoped** — reconectar Prisma a cada teste mata performance. Mantenha session-scoped, limpe via `clean_database`.
- **Misturar unit e integration no mesmo arquivo** — separar por diretório (`test/unit/` vs `test/integration/`) para rodar seletivamente.
- **Esquecer marker `@pytest.mark.integration`** ou `pytestmark = pytest.mark.integration` — CI rápido (`pytest -m "not integration"`) acaba rodando integração e fica lento/instável.

## Verification checklist (antes de entregar)

- [ ] Arquivo em `test/integration/<mirror>/test_<basename>.py`.
- [ ] `pytestmark = pytest.mark.integration` no topo (ou marker individual).
- [ ] `test/integration/conftest.py` existe com fixtures `db`, `client`, `clean_database`.
- [ ] Seeds usam `seed_<entity>` de `test/factories/<feature>.py`; payloads HTTP usam `make_create_<entity>_request(...).model_dump(mode="json")`. Sem `_seed_*` locais nem dicts crus duplicando defaults.
- [ ] `DATABASE_URL_TEST` (ou equivalente) aponta para banco separado do dev.
- [ ] Para cada endpoint: ≥ 1 happy path + ≥ 1 erro de domínio (404/409/422).
- [ ] Asserts em HTTP **e** no DB (estado persistido).
- [ ] Sem `time.sleep`, sem retry, sem ordem implícita.
- [ ] `pytest test/integration -v -m integration` verde 3× em sequência.
