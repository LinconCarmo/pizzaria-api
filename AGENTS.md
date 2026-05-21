# AGENTS.md

Entrypoint vendor-neutro para coding agents (Codex, Cursor, Aider, Claude Code, …) trabalhando no `pizzaria-api`. Segue o padrão [agents.md](https://agents.md/).

## Overview

API backend para gerenciamento de usuários, pedidos e produtos de uma pizzaria. Arquitetura: **Layered Modular Monolith** em FastAPI ("NestJS-like" em Python). Cada feature vive em `src/modules/<feature>/` com camadas explícitas (controller → service → repository).

## Stack

- **Runtime**: Python 3.13.1, `uv` para tooling.
- **Framework**: FastAPI + Pydantic v2.
- **Persistência**: Prisma (client Python) + MySQL.
- **Infra**: Redis, RabbitMQ (subidos via `docker compose`).
- **Qualidade**: ruff (lint + format), mypy (strict), pytest (+ marker `integration`).

## Setup

Setup completo (clone, `uv sync`, `docker compose up`, `.env`) está em [`README.md`](README.md). Este documento foca em **convenções** para agents.

## Comandos comuns

Tudo via `poe` (poethepoet). Definições canônicas em `[tool.poe.tasks]` de [`pyproject.toml`](pyproject.toml).

| Intent | Comando |
|---|---|
| Lint | `poe lint` |
| Format (aplica) | `poe format` |
| Format (check) | `poe format-check` |
| Type-check | `poe type-check` |
| Testes unitários | `poe test` (alias: `poe test-unit`) |
| Testes de integração | `poe test-integration` |
| Cobertura | `poe test-cov` |
| Prisma — gerar client | `poe prisma-generate` |
| Prisma — migrar (dev) | `poe prisma-migrate-dev` |
| Prisma — deploy migrations | `poe prisma-deploy` |
| Dev server | `poe start-dev` |
| Pipeline CI local | `poe ci` (lint → format-check → type-check → test) |

## Arquitetura

**Fonte canônica** (leia antes de implementar qualquer feature não-trivial):

- [`docs/architecture/modular-monolith.md`](docs/architecture/modular-monolith.md) — guideline completo (camadas, persistência, DI, erros, testes, armadilhas).
- [`docs/adr/0001-adotar-modular-monolith-em-camadas.md`](docs/adr/0001-adotar-modular-monolith-em-camadas.md) — decisão arquitetural.

### Non-negotiable (resumo)

- **Estrutura de módulo** (`src/modules/<feature>/`): `__init__.py`, `router.py`, `controllers/v1/<feature>.py`, `service.py`, `repository.py`, `schema.py`, `dependencies.py`. O `router.py` agrega `controllers/v1/` (e futuras `v2/`, `v3/`). Arquivos curtos, **sem prefixo do módulo** na raiz (`service.py`, não `users.service.py`). Dentro de `controllers/v1/`, o arquivo segue o recurso (`users.py`, `orders.py`).
- **Camadas**:
  - **Controller** — recebe/retorna Pydantic, chama service. Sem regra de negócio. Sem `try/except`.
  - **Service** — regra, orquestração, transações. Lança `DomainError`. **Não importa Prisma**.
  - **Repository** — único que toca Prisma. Define `Protocol` + implementação.
  - **Schema** — Pydantic v2 com `Request` e `Response` separados.
- **DI**: `dependencies.py` por módulo expõe providers (`get_<feature>_repository`, `get_<feature>_service`); FastAPI `Depends()` wirea tudo. **Proibido `@staticmethod`**.
- **Exceções de domínio**: `src/core/exceptions.py` — `DomainError`, `NotFoundError`, `ConflictError`, `ValidationError`, `UnauthorizedError`. Handlers globais já registrados em `src/main.py`. **Proibido `HTTPException` na service.**
- **Cross-cutting**: `src/core/` (config, logger, exceptions, middlewares, security) — `src/infra/` (database/Prisma) — `src/shared/` (utils, types compartilhados).
- **Comunicação cross-module**: sempre via `Protocol` exportado pelo módulo dono. Nunca importar Prisma de outro módulo.

## Playbooks operacionais

Guias passo-a-passo para tarefas comuns. **Conteúdo é prosa + templates portáveis** — qualquer agent que leia este arquivo pode segui-los. O diretório `.claude/skills/` é o path de auto-descoberta do Claude Code (limitação atual da ferramenta); o markdown dentro é vendor-neutro.

| Playbook | Path | Quando usar |
|---|---|---|
| `create-module` | [`.claude/skills/create-module/SKILL.md`](.claude/skills/create-module/SKILL.md) | Scaffold de uma feature nova em `src/modules/<feature>/` |
| `create-endpoint` | [`.claude/skills/create-endpoint/SKILL.md`](.claude/skills/create-endpoint/SKILL.md) | Adicionar endpoint a um módulo existente |
| `pydantic-schema` | [`.claude/skills/pydantic-schema/SKILL.md`](.claude/skills/pydantic-schema/SKILL.md) | Criar/refatorar DTOs Request/Response Pydantic v2 |
| `pytest-unit` | [`.claude/skills/pytest-unit/SKILL.md`](.claude/skills/pytest-unit/SKILL.md) | Testes unitários (sem DB) com mocks tipados |
| `pytest-integration` | [`.claude/skills/pytest-integration/SKILL.md`](.claude/skills/pytest-integration/SKILL.md) | Testes de integração (Prisma + MySQL real via docker) |
| `logger-level-choice` | [`.claude/skills/logger-level-choice/SKILL.md`](.claude/skills/logger-level-choice/SKILL.md) | Escolher nível (DEBUG/INFO/WARNING/ERROR/CRITICAL) ao adicionar um log |
| `logger-message-structure` | [`.claude/skills/logger-message-structure/SKILL.md`](.claude/skills/logger-message-structure/SKILL.md) | Escrever a mensagem: `event_name` em inglês, `bind(...)`, `exception()`, sem PII |
| `logger-config-performance` | [`.claude/skills/logger-config-performance/SKILL.md`](.claude/skills/logger-config-performance/SKILL.md) | Configurar `LOG_LEVEL`, sinks, lazy eval e rate limit em hot paths |
| `pizzaria-reviewer` | [`.claude/skills/pizzaria-reviewer/SKILL.md`](.claude/skills/pizzaria-reviewer/SKILL.md) | Code review contra os padrões arquiteturais — use antes de PR ou para auditar módulo existente |

## Convenções de teste

- **Padrão AAA** (Arrange / Act / Assert) explícito.
- **`test/unit/`** — sem hit em DB, HTTP, Redis, RabbitMQ. Mocks via `spec=`.
- **`test/integration/`** — usa Prisma + MySQL real (docker-compose). Marker `@pytest.mark.integration`. `httpx.AsyncClient` para exercitar o pipeline HTTP do FastAPI.
- **Factories** centralizadas em `test/factories/<feature>.py` (`make_<entity>_row`, `make_<entity>_response`, `make_create_<entity>_request`, `seed_<entity>`).
- **Sem `asyncio_mode` manual** — está em `pyproject.toml` (`asyncio_mode = "auto"`).

## Tooling específico do Claude Code (opcional)

Os arquivos abaixo só fazem sentido dentro do Claude Code (usam frontmatter proprietário `tools`/`model`/`color`). Outros agents podem ignorá-los.

- [`.claude/agents/fastapi-architect.md`](.claude/agents/fastapi-architect.md) — sub-agent de planejamento (read-only) que transforma requisitos em planos técnicos.
- [`.claude/agents/pizzaria-reviewer.md`](.claude/agents/pizzaria-reviewer.md) — sub-agent de code review contra estes padrões.
- `CLAUDE.md` — wrapper de 1 linha que importa este arquivo (`@AGENTS.md`). Existe porque Claude Code não lê `AGENTS.md` nativamente.
