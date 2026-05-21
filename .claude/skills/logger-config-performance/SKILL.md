---
name: logger-config-performance
description: Configurar e ajustar o logger do pizzaria-api — `LOG_LEVEL` por ambiente, sinks adicionais (arquivo/auditoria), lazy evaluation em hot paths, rate limiting em loops, separação de destinos para logs operacionais vs auditoria. Use quando estiver mexendo em [`src/core/logger.py`](../../../src/core/logger.py), tunando performance em código que loga muito, adicionando um novo sink, ou debugando configuração de logs em prod/staging/dev.
---

# Logger Config & Performance Skill

Use esta skill para tudo que envolva **configuração do logger global**, **destinos de log** e **performance em pontos de alto throughput**. **Escolha de nível** fica na skill `logger-level-choice`. **Formato da mensagem por chamada** fica na skill `logger-message-structure`.

> Referência arquitetural: [`docs/architecture/modular-monolith.md`](../../../docs/architecture/modular-monolith.md) (seção "Logging"). Decisão: [ADR 0002](../../../docs/adr/0002-padroes-de-logging.md). Setup atual: [`src/core/logger.py`](../../../src/core/logger.py).

## Quando usar

- Vai alterar [`src/core/logger.py`](../../../src/core/logger.py) (adicionar sink, mudar formato, ajustar patcher).
- Está debugando "por que meus logs DEBUG não aparecem" / "por que prod está logando demais".
- Está adicionando log em um **hot path** (loop, handler chamado milhares de vezes/segundo).
- Precisa de um sink separado para auditoria/segurança.
- Vai mexer em `LOG_LEVEL`, `APP_ENV` ou variáveis relacionadas em `.env` / [`src/core/config.py`](../../../src/core/config.py).

## Quando NÃO usar

- Só quer escolher o nível de uma chamada nova → `logger-level-choice`.
- Só quer estruturar a mensagem e os campos → `logger-message-structure`.
- Está usando o logger no modo normal em código de feature — não precisa configurar nada.

## Setup atual (snapshot)

[`src/core/logger.py`](../../../src/core/logger.py):

- **Único sink**: `sys.stdout` em formato texto (dev/test) ou JSON serializado (prod).
- **Nível**: lido de `settings.log_level` (default `INFO`, configurável via env var `LOG_LEVEL`).
- **Cor**: habilitada em `app_env == "development"`.
- **Patcher global**: `_patcher` aplica redaction (lista `SENSITIVE_KEYS`) e injeta `request_id` a partir de `request_id_var`.

## Configuração por ambiente

Variáveis em `.env` (ver [`.env.example`](../../../.env.example)):

| Env         | `APP_ENV`     | `LOG_LEVEL`        | Serialize | Color |
|-------------|---------------|---------------------|-----------|-------|
| Dev local   | `development` | `DEBUG` ou `INFO`   | Não       | Sim   |
| Test (CI)   | `test`        | `INFO` ou `WARNING` | Não       | Não   |
| Staging     | `production`  | `INFO`              | Sim (JSON)| Não   |
| Production  | `production`  | `INFO` ou `WARNING` | Sim (JSON)| Não   |

**Ajuste em runtime**: como `LOG_LEVEL` vem de env var, mudar o nível em prod sem redeploy depende da plataforma (reiniciar pod com env atualizada). Para mudança dinâmica de verdade, seria preciso um endpoint admin chamando `logger.remove() + logger.add(...)` com novo nível — **não implementado**; abrir ADR se virar requisito.

## Lazy evaluation — o que importa

Loguru **já é lazy** para o nível: se o sink ativo tem nível mínimo `INFO`, uma chamada `logger.debug(...)` não chega a renderizar o `format` nem chamar o `patcher`. Isso vale **somente para a renderização** — argumentos passados como kwargs do `bind()` ainda são avaliados.

```python
# ✅ Loguru não renderiza extra se DEBUG está desligado — barato
logger.bind(payload=small_dict).debug("payload_dump")

# ⚠️ A f-string roda ANTES de chegar no logger — caro mesmo com DEBUG desligado
logger.debug(f"payload: {json.dumps(huge_payload)}")  # json.dumps sempre roda

# ✅ Use bind com o objeto cru — só serializa se o sink consumir
logger.bind(payload=huge_payload).debug("payload_dump")
```

**Para argumentos caros** (computação para gerar a string), bloqueie a avaliação com guard explícito:

```python
if logger.level("DEBUG").no >= logger._core.min_level:  # nível ativo
    expensive = compute_expensive_dump()
    logger.bind(snapshot=expensive).debug("snapshot")
```

Na prática, o padrão acima é raro — quase sempre basta passar o objeto cru via `bind` e deixar o sink decidir.

## Hot paths: loops e handlers chamados em massa

Não logar por iteração. Padrões aceitáveis:

### Agregação no fim do loop

```python
processed = 0
skipped = 0
for item in items:
    try:
        await self._process(item)
        processed += 1
    except SkipItem:
        skipped += 1

logger.bind(processed=processed, skipped=skipped, total=len(items)).info("batch_finished")
```

### Amostragem (1 a cada N)

```python
for idx, item in enumerate(items):
    await self._process(item)
    if idx % 1000 == 0:
        logger.bind(progress=idx, total=len(items)).info("batch_progress")
```

### Rate limit por tempo

```python
last_log = 0.0
for item in stream:
    await self._process(item)
    now = perf_counter()
    if now - last_log > 5.0:  # no máximo 1 log a cada 5s
        logger.bind(item_id=item.id).debug("processing")
        last_log = now
```

## Sinks adicionais — quando adicionar

Hoje só existe `sys.stdout`. Cenários que justificam um sink novo:

1. **Auditoria** (compliance/legal — quem fez o quê e quando): sink separado para evento específico, geralmente em arquivo append-only ou tópico Kafka. **Mistura com logs operacionais é antipattern**: requisitos de retenção, redação e acesso são diferentes.
2. **Telemetria estruturada para um destino externo** (Datadog, Loki, CloudWatch). Geralmente via agent externo lendo stdout JSON em prod — não precisa de sink Python, basta `serialize=True`.
3. **Arquivo local em dev** para tail offline. Útil em casos pontuais; não comitar.

### Padrão para sink de auditoria (template — só implementar quando houver requisito)

```python
# src/core/logger.py — exemplo, NÃO implementado
audit_logger = logger.bind(audit=True)

logger.add(
    "audit.log",
    rotation="100 MB",
    retention="365 days",
    filter=lambda record: record["extra"].get("audit") is True,
    serialize=True,
)
```

Uso:

```python
audit_logger.bind(actor_id=user.id, action="user_deleted", target_id=target.id).info("audit_event")
```

> **Se virar requisito**, abrir ADR (`0003-logs-de-auditoria.md`) com: critério de eventos auditáveis, retenção, acesso, sink (arquivo? Kafka? S3?), formato.

## Patcher global — quando estender

[`src/core/logger.py:_patcher`](../../../src/core/logger.py) faz redaction e injeta `request_id`. Extensões possíveis:

- **Mais chaves sensíveis**: editar `SENSITIVE_KEYS` (ordene por categoria). Adicionar test em [`test/unit/core/test_logger.py`](../../../test/unit/core/test_logger.py).
- **Outro ContextVar**: ex.: `trace_id` para integração com tracing distribuído. Mesmo padrão de `request_id_var`.
- **Truncar payloads gigantes**: se ficar comum, adicionar truncamento no patcher (`len(json.dumps(value)) > LIMIT`) antes do sink.

**Não estender** o patcher para:

- Filtrar logs por conteúdo (use `filter=` no `logger.add` específico).
- Adicionar campos derivados de payload (responsabilidade do chamador via `bind`).

## Anti-padrões

- **`print(...)` no código de produção**: bypassa nível, formato, redaction e correlation. Sempre `logger.<level>(...)`.
- **`logger.add(...)` espalhado por módulos**: a config é centralizada em [`src/core/logger.py`](../../../src/core/logger.py). Adicionar sink em outro lugar quebra a previsibilidade.
- **`logging.getLogger(...)`** (stdlib): o projeto usa `loguru`. Não misturar.
- **Mudar nível em runtime via flag in-memory** (sem ADR / endpoint admin auditado): vira "alguém ligou DEBUG em prod e esqueceu". Mantenha por env var + restart.
- **Sink de arquivo committed no repositório** (`logger.add("debug.log")` em código de feature): use stdout, deixe o coletor externo (Datadog/Loki/CloudWatch) cuidar de persistência.
- **F-string em hot path para DEBUG**: a f-string roda mesmo com DEBUG off. Use `bind`.
- **Misturar log de auditoria com log operacional** no mesmo sink: requisitos legais ≠ requisitos de debug.

## Verification checklist

- [ ] Nenhuma chamada `logger.add(...)` fora de [`src/core/logger.py`](../../../src/core/logger.py).
- [ ] `LOG_LEVEL` controlado por env var, sem hardcode.
- [ ] Hot paths usam agregação/amostragem/rate limit — não logam por iteração.
- [ ] F-strings caras (JSON dumps, model_dump full) **não** estão em logs `DEBUG` em hot paths.
- [ ] Nenhum `print(...)` introduzido (use logger).
- [ ] Se adicionou chave em `SENSITIVE_KEYS`, há teste em `test/unit/core/test_logger.py` cobrindo.
- [ ] Sinks novos respondem a um requisito real (auditoria/compliance) e estão documentados em ADR.
