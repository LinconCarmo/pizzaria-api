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

Tudo via `poe` (poethepoet); definições em `[tool.poe.tasks]` de [`pyproject.toml`](pyproject.toml). Os mais usados: `poe lint`, `poe format`, `poe type-check`, `poe test`, `poe test-integration`, `poe ci`.

> **Tabela completa**: [`docs/architecture/conventions.md#comandos`](docs/architecture/conventions.md#comandos).

## Arquitetura

**Fonte canônica** (leia antes de implementar qualquer feature não-trivial):

- [`docs/architecture/conventions.md`](docs/architecture/conventions.md) — **regras normativas** (o "o quê / deve"), fonte única referenciada por todos.
- [`docs/architecture/modular-monolith.md`](docs/architecture/modular-monolith.md) — detalhamento (exemplos, templates, rationale) dessas regras.
- [`docs/adr/`](docs/adr/) — decisões (o porquê): [0001](docs/adr/0001-adotar-modular-monolith-em-camadas.md) padrão, [0003](docs/adr/0003-ids-uuid.md) UUID, [0004](docs/adr/0004-naming-com-prefixo-de-entidade.md) naming.

### Non-negotiable (índice)

Regras normativas completas em [`conventions.md`](docs/architecture/conventions.md). Resumo dos inegociáveis e suas âncoras:

- **Naming** — arquivos `snake_case` prefixados pela entidade (`user_service.py`, **não** `service.py` nem `user.service.py`). → [#naming](docs/architecture/conventions.md#naming)
- **Camadas** — `controller → service → repository`; service não importa Prisma; repository é o único que toca. → [#camadas](docs/architecture/conventions.md#camadas)
- **DI** — `Annotated[T, Depends(...)]` em `<entity>_dependencies.py`; **proibido `@staticmethod`**. → [#di](docs/architecture/conventions.md#di)
- **Erros** — `DomainError` + subclasses; **proibido `HTTPException` na service**; handlers globais em `src/main.py`. → [#erros](docs/architecture/conventions.md#erros)
- **Pydantic** — `Request`/`Response` separados; `Decimal` p/ money; `uuid.UUID` p/ ids. → [#pydantic](docs/architecture/conventions.md#pydantic) · [#uuid](docs/architecture/conventions.md#uuid)
- **`Any` é banido** (ruff `TID251`) — sem `cast(Any)`; tipar args do Prisma com `types.*`. → [#tipos](docs/architecture/conventions.md#tipos)
- **Cross-module** — sempre via `Protocol` do módulo dono; nunca importar Prisma de outro módulo. → [#camadas](docs/architecture/conventions.md#camadas)
- **Cross-cutting**: `src/core/` (config, logger, exceptions, middlewares, security) — `src/infra/` (database/Prisma) — `src/shared/` (utils, types compartilhados).

## Playbooks operacionais

Guias passo-a-passo para tarefas comuns. **Conteúdo é prosa + templates portáveis** — qualquer agent que leia este arquivo pode segui-los. O diretório `.claude/skills/` é o path de auto-descoberta do Claude Code (limitação atual da ferramenta); o markdown dentro é vendor-neutro.

| Playbook                    | Path                                                                                                     | Quando usar                                                                                    |
| --------------------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `create-module`             | [`.claude/skills/create-module/SKILL.md`](.claude/skills/create-module/SKILL.md)                         | Scaffold de uma feature nova em `src/modules/<feature>/`                                       |
| `create-endpoint`           | [`.claude/skills/create-endpoint/SKILL.md`](.claude/skills/create-endpoint/SKILL.md)                     | Adicionar endpoint a um módulo existente                                                       |
| `prisma-migration`          | [`.claude/skills/prisma-migration/SKILL.md`](.claude/skills/prisma-migration/SKILL.md)                   | Alterar `schema.prisma` e gerar/aplicar a migration correspondente                             |
| `pydantic-schema`           | [`.claude/skills/pydantic-schema/SKILL.md`](.claude/skills/pydantic-schema/SKILL.md)                     | Criar/refatorar DTOs Request/Response Pydantic v2                                              |
| `pytest-unit`               | [`.claude/skills/pytest-unit/SKILL.md`](.claude/skills/pytest-unit/SKILL.md)                             | Testes unitários (sem DB) com mocks tipados                                                    |
| `pytest-integration`        | [`.claude/skills/pytest-integration/SKILL.md`](.claude/skills/pytest-integration/SKILL.md)               | Testes de integração (Prisma + MySQL real via docker)                                          |
| `logger-level-choice`       | [`.claude/skills/logger-level-choice/SKILL.md`](.claude/skills/logger-level-choice/SKILL.md)             | Escolher nível (DEBUG/INFO/WARNING/ERROR/CRITICAL) ao adicionar um log                         |
| `logger-message-structure`  | [`.claude/skills/logger-message-structure/SKILL.md`](.claude/skills/logger-message-structure/SKILL.md)   | Escrever a mensagem: `event_name` em inglês, `bind(...)`, `exception()`, sem PII               |
| `logger-config-performance` | [`.claude/skills/logger-config-performance/SKILL.md`](.claude/skills/logger-config-performance/SKILL.md) | Configurar `LOG_LEVEL`, sinks, lazy eval e rate limit em hot paths                             |
| `pizzaria-reviewer`         | [`.claude/skills/pizzaria-reviewer/SKILL.md`](.claude/skills/pizzaria-reviewer/SKILL.md)                 | Code review contra os padrões arquiteturais — use antes de PR ou para auditar módulo existente |
| `fastapi-architect`         | [`.claude/skills/fastapi-architect/SKILL.md`](.claude/skills/fastapi-architect/SKILL.md)                 | Planejar feature antes de implementar — transforma requisitos em plano técnico detalhado       |

## Convenções de teste

Regras completas em [`conventions.md#testes`](docs/architecture/conventions.md#testes). Em resumo: **AAA** explícito; `test/unit/` sem I/O (mocks via `spec=`); `test/integration/` com Prisma + MySQL real e marker `@pytest.mark.integration`; factories em `test/factories/<entity>_factory.py`; arquivos de teste em `snake_case` espelhando a origem (`test_<entity>_service.py`); **sem `Any`**.

## Tooling específico do Claude Code (opcional)

Os arquivos abaixo só fazem sentido dentro do Claude Code (usam frontmatter proprietário `tools`/`model`/`color`). Outros agents podem ignorá-los.

- [`.claude/agents/fastapi-architect.md`](.claude/agents/fastapi-architect.md) — sub-agent de planejamento exclusivo para Claude Code. Para uso em outros providers, prefer a skill vendor-neutra [`.claude/skills/fastapi-architect/SKILL.md`](.claude/skills/fastapi-architect/SKILL.md).
- `CLAUDE.md` — wrapper de 1 linha que importa este arquivo (`@AGENTS.md`). Existe porque Claude Code não lê `AGENTS.md` nativamente.
