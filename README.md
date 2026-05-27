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
uv run poe prisma-migrate-create   # gera a migration (--create-only)
uv run poe prisma-migrate-run       # aplica as migrations pendentes
uv run poe prisma-seed              # semeia os roles padrão (idempotente)

# Dev server
uv run poe start-dev
```

Após `start-dev`, Swagger/OpenAPI disponível em <http://127.0.0.1:8000/docs>.

## Comandos do dia-a-dia

Tasks definidas em [`pyproject.toml`](pyproject.toml) (`[tool.poe.tasks]`). Executar com `uv run poe <task>`. Mais usados: `poe lint`, `poe format`, `poe type-check`, `poe test`, `poe test-integration`, `poe ci`.

**Tabela completa**: [`docs/architecture/conventions.md#comandos`](docs/architecture/conventions.md#comandos).

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
└── main.py

test/
├── unit/              # sem DB/HTTP/Redis/RabbitMQ
├── integration/       # Prisma + MySQL real (marker @pytest.mark.integration)
└── factories/         # builders compartilhados (make_*, seed_*)
```

Cada módulo em `src/modules/<feature>/` segue o layout (arquivos em **`snake_case` prefixados pela entidade** singular `<entity>`; controller versionado em `controllers/v1/`):

```text
__init__.py | <entity>_router.py | controllers/v1/<entity>_controller.py | <entity>_service.py | <entity>_repository.py | <entity>_schema.py | <entity>_dependencies.py
```

Ex. concreto (`users`): `user_service.py`, `user_repository.py`, `controllers/v1/user_controller.py`. Regra de naming/estrutura: [`conventions.md#naming`](docs/architecture/conventions.md#naming) · [`#estrutura`](docs/architecture/conventions.md#estrutura) (decisão em [ADR 0004](docs/adr/0004-naming-com-prefixo-de-entidade.md)).

**Regras normativas**: [`docs/architecture/conventions.md`](docs/architecture/conventions.md). **Detalhes (camadas, DI, erros, persistência, testes, armadilhas)**: [`docs/architecture/modular-monolith.md`](docs/architecture/modular-monolith.md).

## Documentação adicional

- [`AGENTS.md`](AGENTS.md) — convenções para coding agents (vendor-neutro, padrão [agents.md](https://agents.md/)).
- [`docs/architecture/conventions.md`](docs/architecture/conventions.md) — regras normativas (fonte única).
- [`docs/architecture/modular-monolith.md`](docs/architecture/modular-monolith.md) — guideline arquitetural completo (detalhamento).
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
