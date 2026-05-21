# ADR 0002 — Padrões de Logging

- **Status:** Aceito
- **Data:** 2026-05-21
- **Autor:** Martin Morães
- **Supersede:** —
- **Superseded by:** —

## Contexto

O `pizzaria-api` adotou `loguru` na rodada de infraestrutura (commit `dd37adf`, "infra: add loguru"), mas o setup inicial cobria apenas o básico: um sink em `sys.stdout`, nível controlado por env var (`LOG_LEVEL`) e serialização JSON em produção. Faltavam três coisas críticas para um backend que processa pedidos, autentica usuários e lida com PII brasileira:

1. **Sanitização de dados sensíveis.** Senhas, tokens JWT, CPF/CNPJ, dados de cartão e PII (`email`, `phone`, `address`) podiam vazar em logs caso um desenvolvedor passasse um payload inteiro ou usasse f-string com dados sensíveis. Sob LGPD, isso é risco regulatório direto.

2. **Correlation ID propagado.** O `LoggingMiddleware` já gerava `request_id = uuid4()` por request e expunha no header `X-Request-ID`, mas **logs dentro de service/repository não tinham acesso a esse ID** — debugar uma falha distribuída exigia reconstituição manual por timestamp, o que escala mal.

3. **Convenção para agents e desenvolvedores.** Sem regras explícitas sobre níveis (DEBUG/INFO/WARNING/ERROR/CRITICAL), formato de mensagem, mensagens em inglês, lazy evaluation e separação de auditoria/operacional, cada chamada de log refletia a preferência individual do autor — produzindo dashboards ruidosos, ERROR para validação de input, mensagens em português que não casam com ferramentas, e logs em loops apertados.

Precisávamos de uma decisão formal que cobrisse esses três pontos de forma vinculante e auditável.

## Decisão

Adotamos um **conjunto coeso de padrões de logging** sobre `loguru`, com três peças principais:

### 1. Patcher global de sanitização e correlation

Em [`src/core/logger.py`](../../src/core/logger.py):

- Uma `ContextVar` exportada (`request_id_var`) carrega o ID do request da camada de middleware até qualquer log dentro de service/repository/job no mesmo contexto async.
- Um patcher (`logger.configure(patcher=...)`) aplicado globalmente:
  - **Mascara** recursivamente, em `record["extra"]`, qualquer chave (case-insensitive) presente em `SENSITIVE_KEYS` — credenciais (`password`, `token`, `authorization`, ...), documentos brasileiros (`cpf`, `cnpj`, `rg`), pagamento (`card_number`, `cvv`, `pan`, ...) e PII de contato (`email`, `phone`, `address`, ...).
  - **Injeta** `request_id` em `record["extra"]` a partir de `request_id_var.get()` quando não foi explicitamente passado via `bind()`.

O middleware ([`src/core/middlewares.py`](../../src/core/middlewares.py)) é responsável por `request_id_var.set(...)` no início de cada request e `reset(...)` no `finally` — garantindo isolamento entre requests/tasks async.

### 2. Convenção de uso (capturada por skills)

Três skills vivas em `.claude/skills/` materializam as regras para qualquer agent/desenvolvedor:

- **`logger-level-choice`** — escolha de nível (DEBUG/INFO/WARNING/ERROR/CRITICAL) com heurística "quem vai ler? o que precisa fazer?", tabela de referência rápida e exemplos contextualizados.
- **`logger-message-structure`** — mensagens em inglês como `event_name` snake_case (substantivo), contexto via `logger.bind(...)` (nunca f-string), `logger.exception()` no `except`, nada de logar e re-lançar a mesma exception.
- **`logger-config-performance`** — config por ambiente (`LOG_LEVEL`), lazy evaluation, rate limiting em hot paths, separação de sink para auditoria (não implementado, ver "Consequências").

Regras-chave aplicadas globalmente:

- **Mensagens em inglês**, sempre — independentemente do domínio em português. Ferramentas de observabilidade, busca e bibliotecas trabalham em inglês.
- **Sem `print(...)`** em código de produção.
- **`HTTPException` continua proibido em service** (ADR 0001) — exceptions de domínio (`DomainError`) não devem ser logadas no service; o handler global em [`src/main.py`](../../src/main.py) já loga uma vez.

### 3. Configuração por ambiente, sem mudança em runtime

`LOG_LEVEL` vem de env var via `settings.log_level` ([`src/core/config.py`](../../src/core/config.py)):

- Dev: `DEBUG` ou `INFO`, texto colorizado.
- Test/CI: `INFO`/`WARNING`, texto.
- Prod: `INFO`/`WARNING`, JSON serializado (lido por agent externo — Datadog/Loki/CloudWatch).

Mudança de nível em prod exige restart com env var atualizada. Endpoint admin para toggle em runtime **não está implementado** e fica como gap conhecido — pode virar ADR futuro se requisito de incident response surgir.

## Consequências

### Positivas

- **Sanitização automática.** Desenvolvedores não precisam lembrar de mascarar campos sensíveis manualmente — basta passar via `bind()`. A lista `SENSITIVE_KEYS` é extensível e versionada.
- **Debug distribuído viável.** `request_id` aparece em todos os logs de um request sem qualquer esforço do autor do código. Ferramentas externas (Datadog, Loki) podem agrupar logs por `extra.request_id`.
- **Logs consistentes.** Toda a equipe (e os agents) seguem o mesmo padrão: `event_name` em inglês, contexto estruturado, exceptions com traceback. Dashboards e alertas ficam previsíveis.
- **LGPD-friendly.** Patcher cobre `cpf`, `cnpj`, `email`, `phone`, `address` — diminui materialmente o risco de vazamento por log.
- **Skills materializam a convenção.** Agents (Codex, Cursor, Claude Code) seguem o padrão sem cerimônia adicional — o conhecimento vive no repo.

### Negativas / custos

- **F-strings continuam não cobertas.** Se alguém escrever `logger.info(f"user {email}")`, a string já está formada quando o logger vê — patcher não consegue mascarar. Mitigação: skills documentam isso explicitamente; revisão (humano + `pizzaria-reviewer`) precisa flagar.
- **Lista `SENSITIVE_KEYS` exige manutenção.** Chaves novas (futuro `chave_pix`, `taxpayer_id`, ...) só são mascaradas após PR atualizando a lista. Mitigação: convenção "passar campos específicos, não payloads inteiros" reduz exposure.
- **Patcher tem overhead.** Cópia recursiva de `extra` em toda chamada de log. Para o volume atual de logs, negligível; em hot paths sensíveis, pode importar — mitigação documentada em `logger-config-performance` (amostragem, agregação).
- **Sem sink de auditoria.** Eventos com requisitos legais (deleção de usuário, acesso a dado sensível, ações administrativas) ainda compartilham o mesmo sink que logs operacionais. Quando houver requisito formal de auditoria, abrir ADR `0003-logs-de-auditoria.md` com critério de eventos, retenção e destino (arquivo append-only? Kafka? S3?).
- **Mudança dinâmica de nível em prod não suportada.** Para diagnosticar incidente que precisa de DEBUG em prod, depende de restart com env var atualizada — não é instantâneo. Aceitável no estágio atual; revisitar se virar dor real.

## Alternativas consideradas

- **Manter o setup mínimo do commit `dd37adf` e documentar boas práticas em prosa.** Rejeitado: sem patcher de redaction, redaction de PII vira responsabilidade de quem chama — fadado a falhar. Sem ContextVar para `request_id`, debug distribuído fica impraticável.
- **`logger.contextualize()` por handler em vez de ContextVar global.** Funciona dentro de um único request, mas exige envolver todo o controller em `with logger.contextualize(...)` — verboso e não cobre logs de fundo iniciados dentro do request. ContextVar + patcher é mais leve e funciona em qualquer contexto async.
- **Helper explícito `redact(payload)` que o chamador invoca.** Mais explícito, mas opt-in — quem esquece de chamar não tem proteção. Patcher global resolve o caso default e o helper pode coexistir no futuro se surgir necessidade.
- **Migração para stdlib `logging` (em vez de `loguru`).** Rejeitado: `loguru` já é a stack escolhida ([modular-monolith.md §1](../architecture/modular-monolith.md)), é mais ergonômico e suporta o patcher/ContextVar nativamente.

## Referências

- Guideline operacional (seção 7 — Logging): [`docs/architecture/modular-monolith.md`](../architecture/modular-monolith.md)
- Configuração: [`src/core/logger.py`](../../src/core/logger.py)
- Middleware: [`src/core/middlewares.py`](../../src/core/middlewares.py)
- Skills: [`.claude/skills/logger-level-choice/SKILL.md`](../../.claude/skills/logger-level-choice/SKILL.md), [`.claude/skills/logger-message-structure/SKILL.md`](../../.claude/skills/logger-message-structure/SKILL.md), [`.claude/skills/logger-config-performance/SKILL.md`](../../.claude/skills/logger-config-performance/SKILL.md)
- Testes: [`test/unit/core/test_logger.py`](../../test/unit/core/test_logger.py)
- ADR raiz: [`docs/adr/0001-adotar-modular-monolith-em-camadas.md`](0001-adotar-modular-monolith-em-camadas.md)
