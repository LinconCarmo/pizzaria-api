# Pizzaria API

API backend para gerenciamento de usuários, pedidos e produtos de uma pizzaria. Arquitetura: **Layered Modular Monolith** em FastAPI.

> **Para coding agents (Claude Code, Codex, Cursor, …)**: leia [`AGENTS.md`](AGENTS.md) — convenções, playbooks e links para a arquitetura canônica.

## Stack

- Python 3.13.1, [`uv`](https://docs.astral.sh/uv/) para gerenciamento de ambiente
- FastAPI + Pydantic v2
- Prisma (client Python) + MySQL
- Redis, RabbitMQ
- Docker (infra local)
- ruff (lint/format), mypy (strict), pytest

## Requisitos

- Python 3.13.1
- Docker
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
# Clonar
git clone https://github.com/LinconCarmo/pizzaria-api.git
cd pizzaria-api

# Python
uv python install 3.13.1

# Variáveis de ambiente
cp .env.example .env      # Linux/macOS
# copy .env.example .env  # Windows

# Dependências
uv sync

# Infraestrutura (MySQL, Redis, RabbitMQ)
docker compose up -d

# Banco
uv run poe prisma-migrate-create

# Dev server
uv run poe start-dev
```

Após `start-dev`, Swagger/OpenAPI disponível em <http://127.0.0.1:8000/docs>.

## Comandos do dia-a-dia

Tasks definidas em [`pyproject.toml`](pyproject.toml) (`[tool.poe.tasks]`). Executar com `uv run poe <task>`.

| Intent                     | Comando                                            |
| -------------------------- | -------------------------------------------------- |
| Lint                       | `poe lint`                                         |
| Format (aplica)            | `poe format`                                       |
| Format (check)             | `poe format-check`                                 |
| Type-check                 | `poe type-check`                                   |
| Testes unitários           | `poe test` (alias: `poe test-unit`)                |
| Testes de integração       | `poe test-integration`                             |
| Cobertura                  | `poe test-cov`                                     |
| Prisma - formatar shcema   | `poe prisma-format`                                |
| Prisma — gerar client      | `poe prisma-generate`                              |
| Prisma — migrar (dev)      | `poe prisma-migrate-create`                        |
| Prisma — deploy migrations | `poe prisma-deploy`                                |
| Dev server                 | `poe start-dev`                                    |
| Pipeline local             | `poe ci` (lint → format-check → type-check → test) |
| Instalar pre-commit        | `poe pre-commit-install`                           |

## Infraestrutura local

```bash
docker compose up -d   # subir
docker compose down    # parar
docker ps              # listar containers
```

| Serviço     | Porta |
| ----------- | ----- |
| MySQL       | 3306  |
| RabbitMQ    | 5672  |
| RabbitMQ UI | 15672 |
| Redis       | 6379  |

**RabbitMQ Management UI**: <http://localhost:15672> (usuário/senha do `.env`).

## Variáveis de ambiente

Centralizadas via Pydantic Settings em [`src/core/config.py`](src/core/config.py). Exemplo (ver `.env.example` para a lista completa):

```env
DATABASE_URL=mysql://root:root@localhost:3306/pizzaria
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://guest:guest@localhost:5672
JWT_SECRET=change_me
APP_ENV=development
LOG_LEVEL=debug
```

## Estrutura do projeto

```text
src/
├── core/              # config, logger, exceptions, middlewares, security
├── infra/             # database (Prisma)
├── modules/           # features (1 bounded context = 1 módulo)
│   ├── health/
│   └── users/
├── shared/            # utils e tipos compartilhados
├── app.module.py
└── main.py

test/
├── unit/              # sem DB/HTTP/Redis/RabbitMQ
├── integration/       # Prisma + MySQL real (marker @pytest.mark.integration)
└── factories/         # builders compartilhados (make_*, seed_*)
```

Cada módulo em `src/modules/<feature>/` segue o layout:

```text
__init__.py | router.py | controller.py | service.py | repository.py | schema.py | dependencies.py
```

**Detalhes completos (camadas, DI, erros, persistência, testes, armadilhas)**: ver [`docs/architecture/modular-monolith.md`](docs/architecture/modular-monolith.md).

## Documentação adicional

- [`AGENTS.md`](AGENTS.md) — convenções para coding agents (vendor-neutro, padrão [agents.md](https://agents.md/)).
- [`docs/architecture/modular-monolith.md`](docs/architecture/modular-monolith.md) — guideline arquitetural completo.
- [`docs/adr/`](docs/adr/) — decisões arquiteturais (ADRs).



##Authentication Structure

This project implements a Role-Based Access Control (RBAC) structure using Prisma ORM and MySQL.

### Implemented Models

#### User
Stores authentication credentials and profile information.

- Unique field: `email`

#### Role
Defines user roles within the system.

- Unique field: `name`

#### Permission
Defines granular system permissions.

- Unique field: `code`

---

### Relationships

- A `User` belongs to one `Role`
- A `Role` can have multiple `Permissions`
- A `Permission` can belong to multiple `Roles`

---

### Database Features

- Prisma ORM integration
- MySQL database support
- Prisma migrations
- Automatic timestamps:
  - `created_at`
  - `updated_at`

---

### Migration

```bash
prisma migrate dev --name add_auth_models
```

---

### Prisma Client

```bash
prisma generate
```
