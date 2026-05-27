---
name: prisma-migration
description: Workflow de mudança de schema Prisma no pizzaria-api — editar schema.prisma, gerar e revisar a migration, aplicar no banco local, regenerar o client e semear. Use quando o usuário pedir "criar migration", "alterar o schema", "adicionar campo/coluna/tabela/índice", "rodar migrate", "mudar o banco", ou antes de implementar feature que precisa de model/coluna nova.
---

# Prisma Migration Skill

Use esta skill para o workflow de **mudança de schema → migration** no pizzaria-api: editar
`schema.prisma`, gerar a migration, aplicá-la e regenerar o client Python. Para *usar* o Prisma no
código (repository, tipos, erros), veja `create-module`/`create-endpoint`.

> Regras de schema: [modular-monolith.md §5.9](../../../docs/architecture/modular-monolith.md#59-convenções-de-schemaprisma) (fonte única — não duplicada aqui). Comandos: [conventions.md#comandos](../../../docs/architecture/conventions.md#comandos). Decisão de PK UUID: [ADR 0003](../../../docs/adr/0003-ids-uuid.md).

## Quando usar

- "Adicionar a coluna `phone` em `User`"
- "Criar a tabela `Order` / o model `Product`"
- "Adicionar um índice em `deletedAt`"
- "Mudar o tipo de uma coluna" / "adicionar `@@unique`"
- Antes de `create-module`/`create-endpoint` quando o model ou campo **ainda não existe**.

## Quando NÃO usar

- O model/coluna **já existe** e você só vai escrever repository/service → `create-module` / `create-endpoint`.
- Só vai consultar dados, sem mudar estrutura → não precisa de migration.
- Resetar o banco local de dev (não é mudança de schema) → `uv run poe prisma-migrate-reset`.

## Pre-flight

1. Infra local de pé: `docker compose up -d` (MySQL precisa estar rodando para gerar/aplicar a migration).
2. `.env` com `DATABASE_URL` apontando para o MySQL local.
3. Schema atual: [src/infra/prisma/schema.prisma](../../../src/infra/prisma/schema.prisma).
4. Migrations existentes: [src/infra/prisma/migrations/](../../../src/infra/prisma/migrations/) — uma pasta `<timestamp>_<nome>/` por migration.

## Workflow (ordem importa)

Todos os comandos rodam com `uv run poe <task>` (definidos em [pyproject.toml](../../../pyproject.toml) `[tool.poe.tasks]`).

### 1. Editar `schema.prisma`

Aplicar a mudança seguindo as convenções de [§5.9](../../../docs/architecture/modular-monolith.md#59-convenções-de-schemaprisma). Os inegociáveis:

- PK sempre UUID: `id String @id @default(uuid()) @db.Char(36)` — nunca autoincrement.
- `@map`/`@@map` para snake_case no banco (`createdAt` → `created_at`).
- Dinheiro: `Decimal @db.Decimal(10, 2)` — nunca `Float`.
- **Soft delete**: `deletedAt DateTime? @map("deleted_at")` **obriga** `@@index([deletedAt])` (é filtro quente em todo `where`).
- `@@unique` para chaves de negócio; FKs explícitas via `@relation(fields:, references:)`.

### 2. Formatar — `poe prisma-format`

Normaliza o `schema.prisma`. Roda antes de gerar a migration para o diff ficar limpo.

### 3. Gerar a migration — `poe prisma-migrate-create`

Roda `prisma migrate dev --create-only`: cria a pasta `migrations/<timestamp>_<nome>/migration.sql`
**sem aplicar** e **sem regenerar o client**.

> **Dê um nome descritivo em `snake_case`** (ex.: `add_users_deleted_at_index`). O comando pede o
> nome interativamente; em ambientes de agent sem TTY, o prompt vazio gera uma migration **sem nome**
> (já aconteceu: `20260526213743_`). Se não houver TTY, rode manualmente acrescentando
> `--name <nome>`:
> `uv run prisma migrate dev --schema=src/infra/prisma/schema.prisma --create-only --name <nome>`.

### 4. **Revisar o `migration.sql` gerado** (passo crítico)

Abrir `migrations/<timestamp>_<nome>/migration.sql` e conferir o SQL antes de aplicar. Atenção a
operações **destrutivas/perigosas**:

- `DROP COLUMN` / `DROP TABLE` → perda de dados.
- `ALTER ... NOT NULL` em coluna existente sem default → falha se houver linhas.
- Renomeações que o Prisma interpreta como drop+create.

Se o SQL não refletir a intenção, ajustar o `schema.prisma` e voltar ao passo 2 (apagar a pasta da
migration recém-criada antes de regerar).

### 5. Aplicar — `poe prisma-migrate-run`

Roda `prisma migrate deploy`: aplica as migrations pendentes no banco. (`deploy` é o mesmo comando
usado em produção e no `conftest.py` de integração — ver Gotchas.)

### 6. Regenerar o client — `poe prisma-generate`

`prisma migrate --create-only` **não** regenera o client. Rode `prisma generate` para que
`prisma.models.*` e `prisma.types.*` reflitam o schema novo — necessário para o repository tipar e
`poe type-check` passar.

### 7. Semear, se aplicável — `poe prisma-seed`

Se a mudança adiciona dados de bootstrap (ex.: um novo role), atualize
[src/infra/seed.py](../../../src/infra/seed.py) (`seed_roles` é idempotente via `upsert`) e rode a
seed. Fonte única: a fixture de integração importa `seed_roles` de `seed.py`, então basta editar lá.

### 8. Ajustar o repository e validar tipos

Com o client regenerado, atualizar os `types.*` no `<entity>_repository.py` se a forma de
`data`/`where`/`include` mudou (regra: [§5.4](../../../docs/architecture/modular-monolith.md#54-repository-com-protocol)).
Rodar `poe type-check`.

### 9. Commitar schema + migration **juntos**

`schema.prisma` e a pasta `migrations/<timestamp>_<nome>/` vão **no mesmo commit**. Uma sem a outra
quebra o histórico de migration e a suíte de integração.

## Gotchas

- **`migrate-create` não aplica e não gera client.** É `--create-only` de propósito (para revisar o
  SQL). Os passos 5 (`migrate-run`) e 6 (`generate`) são obrigatórios depois.
- **Migration sem nome.** Sempre passe um nome snake_case descritivo (ver passo 3).
- **Testes de integração aplicam migrations automaticamente.** [test/integration/conftest.py](../../../test/integration/conftest.py)
  roda `prisma migrate deploy` contra um MySQL efêmero (Testcontainers) por sessão. Logo, a migration
  **precisa estar commitada** em `migrations/` para os testes a enxergarem.
- **`ROLES` tem fonte única.** Vive em [src/infra/seed.py](../../../src/infra/seed.py); a fixture
  `seed_roles` de [test/integration/conftest.py](../../../test/integration/conftest.py) **importa**
  `seed_roles` de lá. Ao adicionar/alterar roles, edite **apenas** `seed.py` — testes e runtime não
  divergem.
- **Não rode `migrate-reset` por engano.** `poe prisma-migrate-reset` dropa e recria o banco local —
  útil quando o histórico de migration sai de sincronia em dev, destrutivo em qualquer outro caso.

## Checklist

- [ ] `schema.prisma` segue [§5.9](../../../docs/architecture/modular-monolith.md#59-convenções-de-schemaprisma) (PK UUID, `@map`, `Decimal` p/ dinheiro, índice em `deletedAt` se soft delete).
- [ ] `poe prisma-format` rodado.
- [ ] Migration gerada **com nome** descritivo em snake_case.
- [ ] `migration.sql` revisado — nenhuma operação destrutiva não-intencional.
- [ ] `poe prisma-migrate-run` aplicou sem erro.
- [ ] `poe prisma-generate` rodado; `poe type-check` passa.
- [ ] Seed atualizada (se aplicável) em `src/infra/seed.py` (fonte única; integração importa de lá).
- [ ] `schema.prisma` + pasta da migration no **mesmo commit**.
