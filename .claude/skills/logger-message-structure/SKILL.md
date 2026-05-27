---
name: logger-message-structure
description: Estruturar a mensagem e o contexto de cada chamada de log no pizzaria-api — formato `event_name` em inglês, contexto via `logger.bind(...)`, `logger.exception()` para tracebacks, sem f-strings com dados, sem PII/credenciais em logs. Use quando estiver escrevendo a chamada `logger.X(...)` em si: como nomear o evento, quais campos passar, como tratar exceções, como respeitar o pipeline de sanitização.
---

# Logger Message Structure Skill

Use esta skill para escrever **a mensagem** de cada log e **os campos de contexto**. **Escolha de nível** fica na skill `logger-level-choice`. **Configuração de ambiente, sinks e performance** ficam na skill `logger-config-performance`.

> Referência — regras normativas: [conventions.md#logger](../../../docs/architecture/conventions.md#logger). Detalhe: [modular-monolith.md](../../../docs/architecture/modular-monolith.md) (seção "Logging"). Decisão: [ADR 0002](../../../docs/adr/0002-padroes-de-logging.md). Configuração: [`src/core/logger.py`](../../../src/core/logger.py).

## Quando usar

- Vai chamar `logger.info(...)`/`warning(...)`/`exception(...)` e precisa decidir o formato da mensagem e quais campos passar.
- Está refatorando log antigo com f-string para o padrão estruturado.
- Está adicionando log dentro de service/repository/middleware e quer garantir que `request_id`, sanitização e formato fiquem consistentes.

## Quando NÃO usar

- Precisa decidir o **nível** (DEBUG/INFO/WARNING/...) → `logger-level-choice`.
- Está configurando sink, env var, formatação global ou pensando em performance → `logger-config-performance`.

> As regras normativas (`event_name` inglês snake_case, `bind` não f-string, `request_id` automático, sanitização `SENSITIVE_KEYS`, `logger.exception` em vez de `error(str(e))`, não logar-e-reraise nem logar `DomainError`) vivem em [#logger](../../../docs/architecture/conventions.md#logger). Esta skill é a **expansão prática** delas — o **como** escrever a mensagem e o contexto.

## Padrão `event_name` em inglês

Regra: nome em inglês snake_case ([#logger](../../../docs/architecture/conventions.md#logger)). A mensagem é um **substantivo curto**, descrevendo o evento — não uma frase narrativa.

| ✅ Bom                          | ❌ Ruim                                                   |
|--------------------------------|-----------------------------------------------------------|
| `"order_created"`              | `"Order was created successfully for user X"`             |
| `"payment_capture_failed"`     | `"The payment capture failed for order Y"`                |
| `"user_login_failed"`          | `"Failed to login user with email a@b.c"`                 |
| `"cache_fallback_used"`        | `"Cache was unavailable so we fell back to the database"` |
| `"request_started"`            | `f"Request started | request_id={rid}"`                   |

Por que em inglês:
- Mesmo em projeto BR, ferramentas (Datadog, Loki, CloudWatch), bibliotecas, IDEs e contratação são em inglês.
- Busca por termos canônicos (`payment_failed`, `db_connection_error`) funciona em qualquer doc.
- Mensagens internacionalizadas/traduzidas viram um pesadelo de busca.

## Contexto estruturado, não strings concatenadas

Regra: nunca interpolar variáveis na mensagem; contexto sempre via `logger.bind(...)` ([#logger](../../../docs/architecture/conventions.md#logger)). Como aplicar:

```python
# ✅ Correto
logger.bind(user_id=user.id, action="login", path=request.url.path).info("user_action")

# ❌ Errado — f-string interpola antes do logger ver, perde estruturação e atravessa o patcher de sanitização
logger.info(f"User {user.id} did login at {request.url.path}")
```

Por que estruturado importa:
- **Filtrar/agregar** em ferramentas de observabilidade: `extra.user_id:42` é trivial; regex em string concatenada é frágil.
- **Sanitização automática** ([`src/core/logger.py`](../../../src/core/logger.py)) só consegue mascarar PII/credenciais que estão em `extra`. F-string já interpolou antes do logger ver.
- **Lazy evaluation**: serialização de dicts/objetos só acontece se o sink ativo aceita o nível.

### API loguru: usar `bind`, não kwargs em `info()`

```python
# ✅ Padrão do projeto
logger.bind(order_id=42, status="paid").info("order_paid")

# ❌ Loguru não suporta kwargs como `extra` em info() — os kwargs viram format args
logger.info("order_paid", order_id=42, status="paid")  # render: "order_paid" só, kwargs ignorados sem {}
```

Para escopo mais longo (várias linhas), usar `contextualize`:

```python
with logger.contextualize(order_id=order.id):
    logger.info("order_validation_started")
    await self._validate(order)
    logger.info("order_validation_finished")
```

## Correlation ID — `request_id` é automático

Não passar `request_id=...` manual (regra: [#logger](../../../docs/architecture/conventions.md#logger)). O `LoggingMiddleware` ([src/core/middlewares.py](../../../src/core/middlewares.py)) seta `request_id_var` (ContextVar) no início de cada request; o patcher em [`src/core/logger.py`](../../../src/core/logger.py) injeta o valor em `record["extra"]["request_id"]` automaticamente.

```python
# Em qualquer log dentro de um request HTTP — request_id aparece automaticamente
logger.bind(order_id=42).info("order_created")
# → record["extra"]["request_id"] == "<uuid do request>"
```

Para jobs/workers fora de HTTP, setar manualmente:

```python
from src.core.logger import request_id_var

token = request_id_var.set(str(uuid4()))
try:
    logger.info("job_started")
    await process_job()
finally:
    request_id_var.reset(token)
```

**Não** fazer `logger.bind(request_id=...)` manual — duplica trabalho e pode sobrescrever o valor do contextvar com algo inconsistente.

## Sanitização — `SENSITIVE_KEYS` é automático

Sanitização automática de PII/credenciais é normativa ([#logger](../../../docs/architecture/conventions.md#logger)): o patcher mascara chaves sensíveis em `extra` (recursivo em dicts/listas). Lista canônica em [`src/core/logger.py:SENSITIVE_KEYS`](../../../src/core/logger.py):

- **Credenciais**: `password`, `passwd`, `token`, `access_token`, `refresh_token`, `authorization`, `api_key`, `secret`
- **Documentos BR**: `cpf`, `cnpj`, `rg`
- **Pagamento**: `card`, `card_number`, `cvv`, `ccv`, `pan`
- **Contato/PII**: `email`, `phone`, `telefone`, `address`, `endereco`

**Mesmo assim, evite passar payloads inteiros**. Passe só os campos relevantes. Razões:

1. Volume de log cresce em prod e custa caro.
2. Chaves novas (futuras) podem não estar na lista até alguém atualizar.
3. Stack trace em dump completo pode incluir dados sensíveis em strings literais (não cobertos pelo patcher).

```python
# ✅ Campos específicos
logger.bind(user_id=user.id, role=user.role).info("user_authenticated")

# ⚠️ Aceitável (patcher mascara campos sensíveis), mas evite — payload pode crescer e conter dados não previstos
logger.bind(user=user.model_dump()).info("user_authenticated")

# ❌ NUNCA — f-string já interpolou; patcher não vê
logger.info(f"User authenticated: {user.model_dump()}")
```

Se precisar logar uma chave que está em `SENSITIVE_KEYS` **propositalmente** (ex.: prefixo de token para debug), use outro nome de campo:

```python
logger.bind(token_prefix=token[:6]).debug("token_check")
```

## Exceptions — sempre com traceback

Regra: `logger.exception("event_name")` no `except` (nunca `error(str(e))`), não logar-e-reraise, não logar `DomainError` antes de `raise` ([#logger](../../../docs/architecture/conventions.md#logger)). Loguru captura o traceback automaticamente:

```python
# ✅ Correto
try:
    await self._external_api.call()
except ExternalAPIError:
    logger.bind(operation="capture", order_id=order_id).exception("external_api_call_failed")
    raise

# ❌ Perde o traceback
except ExternalAPIError as e:
    logger.error(str(e))  # só a string da exception, sem stack

# ❌ Logar e re-raise a mesma exception em camadas diferentes → logs duplicados
except ExternalAPIError:
    logger.exception("api_failed")
    raise  # se o caller também logar, vira dupla
```

Regra: **escolha um lado**. Ou loga e trata (não re-raise), ou deixa subir (não loga). O handler global em [src/main.py](../../../src/main.py) já loga `Exception` não tratada uma vez.

Para `DomainError` (esperada): **não logar**. O handler global cuida. Logar duplica.

## Padrão de uso por camada

### Service

```python
class OrderService:
    async def create(self, data: CreateOrderRequest) -> OrderResponse:
        order = await self._repository.create(data)
        logger.bind(
            order_id=order["id"],
            customer_id=data.customer_id,
            total=str(order["total"]),  # Decimal → str para evitar precisão estranha em JSON
        ).info("order_created")
        return OrderResponse.model_validate(order)
```

### Middleware / Worker

```python
# ContextVar setado antes; campos específicos via bind
logger.bind(method=request.method, path=request.url.path).info("request_started")
```

### Repository

Repositórios geralmente **não logam** — é I/O puro. Exceção: tradução de erro Prisma quando útil para diagnóstico.

```python
except UniqueViolationError as exc:
    logger.bind(table="users", constraint="email_unique").warning("unique_violation_translated")
    raise ConflictError(...) from exc
```

## Naming de eventos — convenção do projeto

- **Lowercase snake_case.**
- **Substantivo do evento**, não verbo de ação narrativa. `order_created`, não `creating_order`.
- **Sufixos comuns**: `_started`, `_finished`, `_failed`, `_succeeded`, `_skipped`, `_retried`, `_fallback_used`.
- **Sem pontuação no final.** `"order_created"`, não `"order_created."`.
- **Não repetir nível na mensagem.** Já é o nível do log. `logger.error("error_creating_order")` é redundante; use `"order_create_failed"`.

## Anti-padrões

Os anti-padrões que correspondem a regras compartilhadas (f-string com dados, `request_id=` manual, `logger.error(str(e))`, logar-e-reraise, logar `DomainError` antes de raise, logar PII/credenciais) estão consolidados em [#logger](../../../docs/architecture/conventions.md#logger). Específicos desta skill (formato da mensagem):

- **Mensagens em português / frases narrativas**: dificulta busca e padronização — use `event_name` snake_case em inglês.
- **Logar payloads brutos sem critério**: vira gigabytes em prod e pode vazar campos não previstos; passe só os campos relevantes.

## Exemplo completo

```python
# src/modules/orders/order_service.py
from src.core.logger import logger

from src.core.exceptions import NotFoundError
from src.modules.orders.order_repository import OrderRepositoryProtocol
from src.modules.orders.order_schema import CreateOrderRequest, OrderResponse


class OrderService:
    def __init__(self, repository: OrderRepositoryProtocol, payment: PaymentGatewayProtocol) -> None:
        self._repository = repository
        self._payment = payment

    async def create(self, data: CreateOrderRequest) -> OrderResponse:
        order = await self._repository.create(data)
        logger.bind(order_id=order["id"], customer_id=data.customer_id).info("order_created")
        return OrderResponse.model_validate(order)

    async def confirm(self, order_id: int) -> OrderResponse:
        order = await self._repository.find_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")  # handler global loga

        try:
            await self._payment.capture(order_id)
        except PaymentGatewayError:
            logger.bind(order_id=order_id).exception("payment_capture_failed")
            raise  # handler global cuida do response, mas já temos contexto no log

        logger.bind(order_id=order_id).info("order_confirmed")
        return OrderResponse.model_validate(order)
```

## Verification checklist

- [ ] Mensagem é substantivo snake_case em inglês (`order_created`, não `"Order was created"`).
- [ ] Naming consistente com sufixos `_started`/`_finished`/`_failed`/`_succeeded`.
- [ ] Regras compartilhadas respeitadas — sem f-string com dados, sem `request_id=` manual, sem PII/credenciais inline, `logger.exception` em vez de `error(str(e))`, sem logar-e-reraise nem logar `DomainError` antes de raise ([#logger](../../../docs/architecture/conventions.md#logger)).
