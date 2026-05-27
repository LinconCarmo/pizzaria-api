---
name: logger-level-choice
description: Escolher o nível correto de log (DEBUG/INFO/WARNING/ERROR/CRITICAL) ao adicionar uma chamada `logger.X(...)` em controller, service, repository, middleware ou job no pizzaria-api. Use quando precisar decidir o nível de uma nova chamada de log, revisar logs existentes que parecem ruidosos/insuficientes, ou converter `print()` legado.
---

# Logger Level Choice Skill

Use esta skill para escolher o nível de log apropriado em cada chamada. **Formato da mensagem e contexto estruturado** ficam na skill `logger-message-structure`. **Configuração de ambiente e performance** ficam na skill `logger-config-performance`.

> Referência — regras normativas: [conventions.md#logger](../../../docs/architecture/conventions.md#logger). Detalhe: [modular-monolith.md](../../../docs/architecture/modular-monolith.md) (seção "Logging"). Decisão: [ADR 0002](../../../docs/adr/0002-padroes-de-logging.md). Configuração: [`src/core/logger.py`](../../../src/core/logger.py).

## Quando usar

- "Devo logar isso como INFO ou WARNING?"
- "Esse `try/except` deve usar `logger.error` ou `logger.exception`?"
- "Estou convertendo `print(...)` para logger — qual nível?"
- Revisão sugerindo que um log está no nível errado (ex.: ERROR para input do usuário).

## Quando NÃO usar

- A dúvida é sobre **o que** logar (campos, formato, sanitização) → `logger-message-structure`.
- A dúvida é sobre **como configurar** sinks, env vars, lazy eval → `logger-config-performance`.
- Não vai logar nada — só precisa propagar `request_id`. Já é automático via [`request_id_var`](../../../src/core/logger.py).

## Regra mental

> Pense em **quem vai ler** o log e **o que essa pessoa precisa fazer** ao ver a mensagem. Isso resolve 90% dos casos.

- Ninguém lê em condições normais? → **DEBUG**.
- Auditoria do dia-seguinte quer ver? → **INFO**.
- Merece atenção, mas não exige ação imediata? → **WARNING**.
- Alguém precisa investigar agora? → **ERROR**.
- Aplicação não consegue continuar? → **CRITICAL**.

## Tabela de referência rápida

| Nível      | Visível em prod? | Aciona alerta?         | Exemplo no pizzaria-api                                                                 |
|------------|------------------|------------------------|------------------------------------------------------------------------------------------|
| `DEBUG`    | Não              | Não                    | Payload bruto recebido pelo controller; valor calculado de `total` antes da persistência |
| `INFO`     | Sim              | Não                    | `request_started`, `order_created`, `user_authenticated`, `worker_consumed_message`      |
| `WARNING`  | Sim              | Talvez (se frequente)  | `payment_retry_succeeded`, `cache_fallback_used`, `config_default_applied`, `latency_high` |
| `ERROR`    | Sim              | Sim                    | `prisma_unique_violation_unmapped`, `external_api_request_failed`, exception não recuperável |
| `CRITICAL` | Sim              | Sim — página alguém    | `database_connection_failed_on_startup`, `jwt_secret_missing`                            |

## Heurísticas por camada

### Controller

- **Nada de logs de fluxo normal aqui.** O `LoggingMiddleware` já loga `request_started`/`request_finished` ([src/core/middlewares.py](../../../src/core/middlewares.py)). Não duplicar.
- Sem `try/except` → não há `logger.exception` no controller. Erros viram `DomainError` no service e os handlers globais em [src/main.py](../../../src/main.py) cuidam.

### Service

- **INFO** para eventos de negócio: `order_created`, `payment_captured`, `user_promoted_to_admin`.
- **WARNING** para falhas recuperadas: retry bem-sucedido, fallback para gateway secundário, default aplicado para config ausente.
- **ERROR não** para `DomainError` (`NotFoundError`, `ConflictError`, `ValidationError`): é fluxo esperado, não nível de erro — escolha de nível decorre da regra de não logar `DomainError` ([#logger](../../../docs/architecture/conventions.md#logger)).
- Não logar-e-reraise a mesma exception ([#logger](../../../docs/architecture/conventions.md#logger)).

### Repository

- **DEBUG** para queries detalhadas se útil em diagnóstico (lembre: prod não vê).
- **ERROR/exception** apenas se o repository **decide tratar** um erro do Prisma sem traduzir para `DomainError` (raro). Caso traduza para `DomainError`, **não** logar — quem captura no topo loga.

### Middleware / Background workers / Jobs

- **INFO** para start/finish do job, contadores agregados (não por item).
- **WARNING** para item pulado com motivo conhecido.
- **ERROR** com `logger.exception("job_step_failed")` quando um step falha mas o job continua.
- **CRITICAL** quando o worker não consegue inicializar.

## Anti-padrões

- **ERROR para validação de input do usuário.** `RequestValidationError` (422) e `ValidationError` de domínio (422) são **comportamento esperado**, não falha do sistema. Use **INFO** ou **WARNING** se quiser registrar a tentativa. ERROR aqui polui dashboards e gera alertas falsos.
- **Logar tudo em DEBUG e em INFO "por garantia".** Vira ruído e duplicação. Escolha um nível e mantenha.
- **`logger.error(str(e))`** em vez de `logger.exception("event_name")` (perde traceback) — ver [#logger](../../../docs/architecture/conventions.md#logger).
- **Logar dentro de loops apertados sem rate limit** (`for item in 10_000_items: logger.info(...)`). Em INFO, vira gigabytes; em DEBUG, mata performance. Agregue ou amostre — ver `logger-config-performance`.
- **CRITICAL para tudo que "parece grave".** Reserve para `app não pode continuar`. Se o request pode falhar e o próximo pode passar, é `ERROR`, não `CRITICAL`.
- **Logar e re-raise a mesma exception.** Logs duplicados (você + handler global); escolha um lado — ver [#logger](../../../docs/architecture/conventions.md#logger).

## Exemplos contextualizados

### ✅ Bom

```python
# src/modules/orders/order_service.py
class OrderService:
    async def create(self, data: CreateOrderRequest) -> OrderResponse:
        order = await self._repository.create(data)
        logger.bind(order_id=order["id"], customer_id=data.customer_id).info("order_created")
        return OrderResponse.model_validate(order)

    async def confirm_payment(self, order_id: int) -> None:
        try:
            await self._payment_gateway.capture(order_id)
        except GatewayTimeoutError:
            logger.bind(order_id=order_id).warning("payment_gateway_timeout_retrying")
            await self._payment_gateway.capture(order_id, retry=True)
```

### ❌ Ruim

```python
# ERROR para validação de input — isso é fluxo esperado, não erro do sistema
async def create(self, data: CreateOrderRequest) -> OrderResponse:
    if data.total <= 0:
        logger.error(f"Invalid total: {data.total}")  # ❌ usar WARNING ou nada (DomainError já sinaliza)
        raise ValidationError("Total must be positive")

# logger.error(str(e)) — perde stacktrace
try:
    await self._repository.create(data)
except Exception as e:
    logger.error(str(e))  # ❌ use logger.exception("order_create_failed")
    raise

# Log dentro de loop sem rate limit
for item in items:
    logger.info(f"Processing item {item.id}")  # ❌ amostrar/agregar
```

## Decisão rápida (fluxograma textual)

1. Esse log está ajudando alguém a **fazer algo** se aparecer? Não → DEBUG.
2. É um evento que **finalizou com sucesso** (mesmo após retry)? Sim → INFO (sucesso normal) ou WARNING (precisou de retry/fallback).
3. Algo **falhou** mas a app continua viva? → ERROR. Use `logger.exception(...)` se tiver traceback.
4. A app **não pode continuar**? → CRITICAL + `sys.exit` ou propagação fatal.
5. Em dúvida entre dois níveis adjacentes? Escolha o **mais baixo** (DEBUG > INFO, INFO > WARNING, ...). Ruído é mais caro que sutileza.

## Verification checklist (antes de mergear)

- [ ] Cada `logger.X(...)` tem nível justificável pela tabela acima.
- [ ] Não há `logger.error` para validação de input ou `DomainError` esperada.
- [ ] Regras compartilhadas de `exception` vs `error(str(e))` e "não logar-e-reraise" respeitadas ([#logger](../../../docs/architecture/conventions.md#logger)).
- [ ] Loops apertados não logam por iteração sem amostragem.
- [ ] CRITICAL apenas em falhas de inicialização ou estado fatal.
