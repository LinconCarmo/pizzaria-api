# ADR 0003 — IDs como UUID

- **Status:** Aceito
- **Data:** 2026-05-21
- **Autor:** Martin Morães
- **Supersede:** —
- **Superseded by:** —

## Contexto

A migration inicial do `pizzaria-api` (commit `b94c009`) introduziu `HealthCheck` e `User` com `id Int @id @default(autoincrement())`. Antes que outros agregados (`Order`, `Product`, `OrderItem`, …) fossem adicionados — replicando o padrão `Int` por gravitação —, três preocupações pesaram para reabrir a decisão de PK:

1. **Enumeração externa.** IDs sequenciais expostos em URL (`/users/42`) revelam cardinalidade do recurso e facilitam scraping/enumeração. Em uma API que vai expor pedidos e clientes de uma pizzaria com painel público de status, isso é desejável evitar desde o início.
2. **Geração distribuída futura.** A medida que jobs assíncronos, eventos via RabbitMQ e potencialmente outro serviço passarem a criar entidades, ter um espaço de IDs que não dependa de coordenação com um único banco evita um ponto de acoplamento.
3. **Custo de mudar depois.** Trocar PK em um schema vazio é trivial; trocar com 10 tabelas e FKs já criadas é uma migração que cruza compatibilidade, downtime e backfill. Tomar a decisão agora paga mínimo e fixa o padrão antes de espalhar.

O projeto ainda não tem dados em produção — apenas a migration `20260515225542_init` aplicada localmente com `HealthCheck` — então a janela de baixo custo está aberta.

## Decisão

Adotamos **UUID como tipo dos IDs de toda entidade persistida**, com as quatro escolhas operacionais abaixo:

### 1. UUID v4 gerado pelo banco via Prisma

```prisma
model User {
  id String @id @default(uuid()) @db.Char(36)
  // ...
}
```

`@default(uuid())` é resolvido server-side pelo Prisma client no `create` — código de aplicação **não importa `uuid`** para inserir entidades. Removendo essa responsabilidade do código:
- service/repository não precisam orquestrar geração de ID;
- factories de teste não precisam injetar IDs em paths de criação;
- consistência é garantida pelo schema.

**Por que v4 e não v7?** A intenção original era v7 pela localidade de índice (timestamp embutido nos primeiros 48 bits → inserts ~sequenciais em B-tree). Verificação durante a implementação revelou que o `prisma-client-py 0.15.0` empacota Prisma engine **5.17.0**, que ainda **não aceita argumento em `@default(uuid())`** — `@default(uuid(7))` produz erro de schema validation. Suporte a UUIDv7 foi adicionado em versões posteriores do Prisma. Optamos por v4 agora, com a porta aberta para v7 quando o `prisma-client-py` atualizar — a troca é trivial (uma edição de uma linha no schema + migration).

### 2. `@db.Char(36)` explícito no MySQL

`CHAR(36)` (representação canônica com hífens) ao invés de `BINARY(16)`. Trade-off:
- **A favor de CHAR(36)**: legível em queries ad-hoc, copy-paste de URL bate com linha do banco, sem necessidade de conversão em ferramentas externas.
- **Contra**: ~2.25x mais bytes que `BINARY(16)` (36 vs 16). Em uma base com milhões de linhas e muitos índices em UUIDs, isso vira gigabytes de RAM em InnoDB buffer pool — pode merecer ADR futuro para migrar.

Hoje a legibilidade vence; revisitar quando alguma tabela passar de ~10M linhas.

### 3. Tipo Pydantic é `uuid.UUID`

Schemas Request/Response usam `uuid.UUID`, não `str`:

```python
from uuid import UUID

class UserResponse(_BaseSchema):
    id: UUID = Field(..., examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"])
```

Pydantic v2 valida formato automaticamente (rejeita strings malformadas com 422 sem código manual), FastAPI converte path params `user_id: UUID` automaticamente, e o `/docs` (Swagger) expõe como `string($uuid)` — front-end ganha contrato forte.

### 4. Conversão `UUID → str` apenas na borda do repository

O Prisma Python client espera `str` em `where={"id": ...}` para colunas `String`. O **único** lugar onde `str(user_id)` aparece é dentro de cada método do repository:

```python
async def get_by_id(self, user_id: UUID) -> User | None:
    where: types.UserWhereInput = {"id": str(user_id), "deletedAt": None}
    return await self._db.user.find_first(where=where)
```

Service, controller, factories e testes nunca lidam com `str` de UUID. Mensagens de erro continuam funcionando (`f"User {user_id} not found"` — `UUID` tem `__str__` adequado).

## Consequências

### Positivas
- URLs deixam de expor cardinalidade do recurso.
- Padrão único para todas as entidades futuras — `create-module` e `create-endpoint` (skills) já produzem código com UUID.
- Geração descentralizada possível sem mudança de schema.
- Pydantic + FastAPI fornecem validação de formato gratuita.

### Negativas / Trade-offs aceitos
- **URLs mais longas** (`/users/0190f5a3-1b2c-4abc-9def-0123456789ab` vs `/users/42`) — irrelevante para clientes programáticos; pode incomodar em logs/depuração manual.
- **UUID v4 random tem localidade de índice ruim em InnoDB** — irrelevante enquanto a base for pequena. Plano: migrar para v7 quando `prisma-client-py` suportar.
- **CHAR(36) ocupa mais espaço que BINARY(16)** — trade-off explícito por legibilidade; revisitar quando volumetria justificar.
- **Testes precisam de UUIDs hoisted** (`USER_ID = UUID("00000000-0000-4000-8000-000000000001")`) para legibilidade vs IDs numéricos triviais. Padrão aplicado em `test/unit/modules/users/`.

### Gaps conhecidos
- **UUIDv7 não habilitado** até bump de `prisma-client-py`. Ação: revisitar quando uma versão > 0.15.0 estiver disponível e suportar `@default(uuid(7))`.
- **Sem auditoria do tamanho de índice** automatizada — primeira tabela que crescer >1M linhas deve gerar métrica.

## Arquivos afetados

- [`src/infra/prisma/schema.prisma`](../../src/infra/prisma/schema.prisma) — PKs migradas.
- [`src/infra/prisma/migrations/20260521173558_init/migration.sql`](../../src/infra/prisma/migrations/20260521173558_init/migration.sql) — migration init regenerada (`CHAR(36)`).
- [`src/modules/users/`](../../src/modules/users/) — schema, service, repository, controllers usam `uuid.UUID`.
- [`docs/architecture/modular-monolith.md`](../architecture/modular-monolith.md) §4 (Schemas), §5.4 (Repository), §5.5 (Tipos), §5.9 (Convenções) — atualizados.
- [`.claude/skills/{create-module,create-endpoint,pydantic-schema,pytest-unit,pizzaria-reviewer}/SKILL.md`](../../.claude/skills/) — templates ajustados.
