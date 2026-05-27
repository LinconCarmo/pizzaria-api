# Convenções do pizzaria-api — regras normativas

> **Fonte única e normativa** das regras transversais do projeto (o "o quê / deve").
> Cada regra vive **aqui**. O **detalhamento** (exemplos, templates, rationale) está em
> [`modular-monolith.md`](modular-monolith.md); o **porquê** (decisões) está nos
> [ADRs](../adr/). AGENTS.md e as skills referenciam este arquivo em vez de re-enunciar.

Âncoras: [naming](#naming) · [camadas](#camadas) · [di](#di) · [erros](#erros) · [pydantic](#pydantic) · [uuid](#uuid) · [tipos](#tipos) · [migrations](#migrations) · [testes](#testes) · [logger](#logger) · [openapi](#openapi) · [comandos](#comandos) · [estrutura](#estrutura)

---

<a id="naming"></a>

## Naming de arquivos

- Arquivos em **`snake_case` prefixados pela entidade**: `<entity>_<layer>.py`. Separador `_`, **nunca `.`** (ponto quebra o import em Python).
- Diretório do módulo é **plural** (`<feature>`, ex.: `users`); o **prefixo do arquivo** é o **singular** da entidade (`<entity>`, ex.: `user`).
- Camadas: `<entity>_router.py`, `<entity>_service.py`, `<entity>_repository.py`, `<entity>_schema.py`, `<entity>_dependencies.py`; controller em `controllers/v1/<entity>_controller.py`.
- Testes espelham a origem: `test_<entity>_<layer>.py`. Factories: `test/factories/<entity>_factory.py`.
- **Classes** seguem `PascalCase` prefixado (`UserService`, `UserRepository`) — só o nome do **arquivo** muda.
- ✅ `user_service.py`, `controllers/v1/user_controller.py` · ❌ `user.service.py` (dotted) · ❌ `userService.py` (camelCase) · ❌ `service.py` (sem prefixo).

> Decisão: [ADR 0004](../adr/0004-naming-com-prefixo-de-entidade.md). Detalhes: [modular-monolith.md §3](modular-monolith.md).

---

<a id="camadas"></a>

## Camadas e responsabilidades

Direção de dependência: **controller → service → repository**. Schema é transversal.

- **Controller** — recebe/retorna DTO Pydantic, chama o service. Sem regra de negócio, **sem `try/except`**, **sem `HTTPException`**, sem import de Prisma. Retorno via anotação `-> <Response>`; `status_code=` quando ≠ 200; DI com `Annotated`.
- **Service** — orquestra repositories, aplica regra, monta DTOs. **Nunca importa Prisma** (depende do `<X>RepositoryProtocol`). Lança `DomainError`. **Sem `@staticmethod`**. PATCH usa `model_dump(exclude_unset=True)`.
- **Repository** — **único arquivo que importa Prisma**. Define `<X>RepositoryProtocol` + classe concreta (recebe `db: Prisma`). Retorna `dict[str, object]`/`dict[str, object] | None` (bruto do Prisma via `.model_dump()`), nunca Pydantic nem `prisma.models.*`. `dict` sem parâmetros falha no `mypy --strict` (`disallow_any_generics`). I/O puro, sem regra.
- **Schema** — DTOs Pydantic v2 (ver [#pydantic](#pydantic)).
- **Comunicação cross-module**: importar **Protocol** do módulo dono, nunca a classe concreta nem Prisma de outro módulo.

> Detalhes: [modular-monolith.md §4](modular-monolith.md) e §9. Decisão: [ADR 0001](../adr/0001-adotar-modular-monolith-em-camadas.md).

---

<a id="di"></a>

## Injeção de dependências

- Composição manual com `Depends` do FastAPI — **sem framework de DI externo**. Wiring em `<entity>_dependencies.py`.
- Usar **`Annotated[T, Depends(...)]`** em providers e handlers (não `T = Depends(...)`).
- Providers: `get_<feature>_repository` (recebe `Annotated[Prisma, Depends(get_db)]`) e `get_<feature>_service` (recebe o repository via Protocol).
- Service recebe o **Protocol**, não a classe concreta. **Proibido `@staticmethod`**. Reaproveitar `get_db` de `src/infra/database.py`.

> Detalhes: [modular-monolith.md §8](modular-monolith.md).

---

<a id="erros"></a>

## Exceções de domínio

- Hierarquia em `src/core/exceptions.py` → status: `NotFoundError` 404 · `ConflictError` 409 · `ValidationError` 422 · `UnauthorizedError` 401 · `DomainError` 400 (default).
- **Service lança, controller nunca captura.** Handlers globais em `src/main.py` serializam no envelope `ErrorResponse` (`{"error": {code, message, details}}`).
- **Proibido `HTTPException`** em service/controller. Status novo → nova subclasse de `DomainError`.
- **Erros do Prisma** são traduzidos no repository: `UniqueViolationError` → `ConflictError`, `RecordNotFoundError` → `NotFoundError`.
- Validators Pydantic levantam `ValueError` (→ 422 via handler), nunca `HTTPException`.

> Detalhes: [modular-monolith.md §6](modular-monolith.md) e §5.8.

---

<a id="pydantic"></a>

## Schemas Pydantic v2

- **Request e Response sempre separados** — nunca o mesmo modelo.
- Naming: `Create<R>Request`, `Update<R>Request`, `<R>Response`, `<R>SummaryResponse`, `<R>FilterRequest`.
- Response herda de `_BaseSchema` (ou `shared.types.BaseSchema`) com `from_attributes=True`.
- **Money é `Decimal`**, nunca `float`. IDs (PKs/FKs) são `uuid.UUID` (ver [#uuid](#uuid)).
- **Nunca expor** `password_hash`, tokens ou campos internos em `*Response`.
- Enriquecer `Field(..., description=, examples=)` e usar `json_schema_extra` para exemplo completo no `/docs`.

> Detalhes: [modular-monolith.md §4 (Schema)](modular-monolith.md) e §OpenAPI.

---

<a id="uuid"></a>

## IDs UUID

- PK no Prisma: `id String @id @default(uuid()) @db.Char(36)`. Nunca `Int @id @default(autoincrement())`.
- Tipo nos schemas/handlers/service: **`uuid.UUID`** (Pydantic valida formato; Swagger expõe `string($uuid)`).
- **Conversão `UUID → str` apenas na borda do repository** (`where={"id": str(<feature>_id)}`). Service, controller, factories e testes nunca lidam com `str` de UUID.

> Decisão e detalhes: [ADR 0003](../adr/0003-ids-uuid.md); [modular-monolith.md §5.4/§5.9](modular-monolith.md).

---

<a id="tipos"></a>

## Type safety — `Any` é banido

- **`Any` é banido** (enforced via ruff `TID251` em `typing.Any`). Use tipos concretos, `Protocol`, `object` ou os types gerados do Prisma (`prisma.types.*`).
- **`cast(Any, ...)` é proibido.** Para argumentos do Prisma (`data`/`where`/`include`/`order`), **anotar variáveis** com `types.*` (ex.: `data: types.UserCreateInput = {...}`). Filtro de relação no `where` usa a forma canônica `{"rel": {"is": {...}}}`.
- Caso genuinamente dinâmico → `# noqa: TID251` no import, com justificativa inline.

> Detalhes: [modular-monolith.md §3 e §5.4](modular-monolith.md).

---

<a id="migrations"></a>

## Migrations (Prisma)

- Migrations são **geradas por `prisma migrate`** (`poe prisma-migrate-create`) e **não são editadas manualmente**.
- **Único comentário aceito**: o marcador de step gerado pelo Prisma — comentário de linha SQL no formato `-- <NomeDaOperação>`, com `<NomeDaOperação>` em PascalCase e nada mais na linha. Regex: **`^-- [A-Z][A-Za-z]+$`**.
- Vocabulário fechado (valores do Prisma): `CreateTable`, `AlterTable`, `DropTable`, `RenameTable`, `CreateIndex`, `DropIndex`, `CreateEnum`, `AlterEnum`, `DropEnum`, `AddForeignKey`, `DropForeignKey`, `RedefineTables`, `RedefineIndex`.
- ❌ **Proibido**: comentários explicativos livres, comentários de bloco (`/* … */`) e `#`. Qualquer ajuste vai no `schema.prisma` + nova migration, nunca em comentário no `.sql`.

> Local e comando de geração: [modular-monolith.md §5.1](modular-monolith.md). Comandos: [#comandos](#comandos).

---

<a id="testes"></a>

## Convenções de teste

- **AAA** (Arrange / Act / Assert) com linhas em branco entre blocos. Cada `test_*` ≤ ~15 linhas.
- Naming: `test_<verb>_<expected>_when_<condition>` (inglês). Arquivos espelham a origem: `test_<entity>_<layer>.py`.
- **Sem `Any`**: fixtures e mocks com tipo anotado. **Mocks com `spec=<Class|Protocol>`** (nunca `MagicMock()` cru); `AsyncMock` para coroutines.
- **`test/unit/`** — sem DB/HTTP/Redis/RabbitMQ. **`test/integration/`** — Prisma + MySQL real via Testcontainers; marker `@pytest.mark.integration`; assert no HTTP **e** no DB.
- **Factories** em `test/factories/<entity>_factory.py` (barrel `__init__.py`), keyword-only, sem `Any`. Três variantes: `make_<entity>_row` (SimpleNamespace), `make_<entity>_response`/`make_create_<entity>_request` (Pydantic), `seed_<entity>` (escreve no DB). Não redefinir helpers locais quando há factory.
- Cobertura mínima: ≥ 1 happy path + ≥ 1 erro (404/409/422) por método público. Magic values hoisted como constantes. `asyncio_mode=auto` (em `pyproject.toml`).

> Detalhes: [modular-monolith.md §10](modular-monolith.md).

---

<a id="logger"></a>

## Convenções de logger

- Mensagem é `event_name` em **inglês, snake_case** (substantivo, não frase). Contexto via **`logger.bind(...)`**, nunca f-string com dados nem kwargs em `info()`.
- Em `except`: **`logger.exception("event_name")`** (captura traceback), nunca `logger.error(str(e))`.
- **Não logar e re-lançar** a mesma exception (duplica com o handler global). **Não logar `DomainError`** antes de `raise` — o handler global já loga; `DomainError` é fluxo esperado (não `ERROR`).
- `request_id` é **injetado automaticamente** (middleware + patcher) — não passar manualmente.
- Sanitização **automática** de PII/credenciais via `SENSITIVE_KEYS` em `src/core/logger.py` (recursivo, case-insensitive); ainda assim, passe só os campos relevantes, não payloads inteiros.
- Sem `print(...)`; config de sinks centralizada em `src/core/logger.py` (não espalhar `logger.add`).

> Decisão: [ADR 0002](../adr/0002-padroes-de-logging.md). Detalhes: [modular-monolith.md §7](modular-monolith.md). Skills: `logger-level-choice`, `logger-message-structure`, `logger-config-performance`.

---

<a id="openapi"></a>

## Status codes & OpenAPI

- `responses=` mínimo por verbo: `GET /{id}` → 404 · `POST` → 409 (constraint de unicidade) · `PATCH`/`PUT /{id}` → 404 (+409 quando aplicável) · `DELETE /{id}` → 404 · `POST /{id}/<action>` → 404/409. `422` é automático (global); declarar só quando o consumidor precisa ver no `/docs`. Autenticados acrescentam `401` (e `403` se houver autorização granular).
- Usar `ErrorResponse` de `src/core/exceptions.py` como `model` em `responses=` — não redefinir por módulo.
- `tags`: PascalCase plural do domínio (`Users`, `Orders`). `summary`: imperativo curto em inglês (`Create user`). `description`: só quando há efeito não óbvio.

> Detalhes: [modular-monolith.md §OpenAPI / Swagger](modular-monolith.md).

---

<a id="comandos"></a>

## Comandos (`poe`)

Definições canônicas em `[tool.poe.tasks]` de [`pyproject.toml`](../../pyproject.toml).

| Intent                     | Comando                                            |
| -------------------------- | -------------------------------------------------- |
| Lint                       | `poe lint`                                         |
| Format (aplica)            | `poe format`                                       |
| Format (check)             | `poe format-check`                                 |
| Type-check                 | `poe type-check`                                   |
| Testes unitários           | `poe test` (alias: `poe test-unit`)                |
| Testes de integração       | `poe test-integration`                             |
| Cobertura                  | `poe test-cov`                                     |
| Prisma — formatar schema   | `poe prisma-format`                                |
| Prisma — gerar client      | `poe prisma-generate`                              |
| Prisma — migrar (dev)      | `poe prisma-migrate-create`                        |
| Prisma — deploy migrations | `poe prisma-deploy`                                |
| Dev server                 | `poe start-dev`                                    |
| Pipeline CI local          | `poe ci` (lint → format-check → type-check → test) |
| Instalar pre-commit        | `poe pre-commit-install`                           |

---

<a id="estrutura"></a>

## Estrutura de diretórios

```
src/
├── main.py            # bootstrap FastAPI + registro de routers/handlers
├── core/              # config, logger, exceptions, middlewares, security
├── infra/             # database (Prisma) + prisma/ (schema + migrations)
├── shared/            # utils e tipos genuinamente transversais (minimalista)
└── modules/<feature>/ # 1 bounded context = 1 módulo (ver árvore abaixo)

src/modules/<feature>/             # diretório plural; arquivos com prefixo singular <entity>
├── __init__.py
├── controllers/v1/<entity>_controller.py
├── <entity>_router.py
├── <entity>_service.py
├── <entity>_repository.py
├── <entity>_schema.py
└── <entity>_dependencies.py
```

Testes: `test/unit/<mirror>/`, `test/integration/<mirror>/`, `test/factories/<entity>_factory.py`.

> Detalhes: [modular-monolith.md §2-3](modular-monolith.md).
