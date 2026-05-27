# ADR 0004 — Naming de arquivos com prefixo de entidade (`snake_case`)

- **Status:** Aceito
- **Data:** 2026-05-27
- **Autor:** Martin Morães
- **Supersede:** [ADR 0001](0001-adotar-modular-monolith-em-camadas.md) (apenas quanto ao naming de arquivos)
- **Superseded by:** —

## Contexto

O [ADR 0001](0001-adotar-modular-monolith-em-camadas.md) adotou o Modular Monolith em camadas e, em 2026-05-20, padronizou os arquivos de cada módulo em **layout flat sem prefixo** (`service.py`, `repository.py`, `controllers/v1/<feature>.py`). Antes disso o módulo `users` havia experimentado o estilo NestJS dotted (`users.module.py`, `users.repository.py`).

Dois pontos motivaram revisitar o naming:

1. **Legibilidade ao navegar por arquivos abertos.** Com layout flat, abas/buscas mostram vários `service.py`, `repository.py` idênticos entre módulos — o contexto vem só do diretório pai. Preferência explícita por arquivos auto-descritivos no estilo `*.service.*` do NestJS.
2. **Restrição técnica do Python.** O estilo dotted literal do NestJS (`users.service.py`) **não é importável em Python**: o `.` é separador de pacote, então `from src.modules.users.users.service import …` e `importlib.import_module("…users.service")` falham com `ModuleNotFoundError`. NestJS funciona porque TypeScript importa por string de path; Python importa por identificador pontilhado. O equivalente Pythonico e importável é o **`snake_case` com `_`**: `user_service.py`.

## Decisão

Arquivos de cada módulo usam **`snake_case` prefixado pela entidade**: `<entity>_<layer>.py`, com `_` como separador (nunca `.`).

- O **diretório** do módulo permanece plural (`src/modules/users/`); o **prefixo do arquivo** é o singular da entidade (`user_`).
- Layout por módulo:
  - `user_router.py`, `user_service.py`, `user_repository.py`, `user_schema.py`, `user_dependencies.py`
  - `controllers/v1/user_controller.py` (a pasta `controllers/v1/` de versionamento de URL é mantida)
- **Testes** espelham o arquivo de origem: `test_user_service.py`, `test_user_repository.py`, `test_user_controller.py`, etc.
- **Factories**: `test/factories/<entity>_factory.py` (ex.: `user_factory.py`).
- **Nomes de classe** permanecem `PascalCase` prefixados pela entidade (`UserService`, `UserRepository`, `UserRepositoryProtocol`, `CreateUserRequest`) — **inalterados**; só o nome do **arquivo** muda.

Proibido: naming flat sem prefixo (`service.py`) e dotted (`user.service.py`).

O **como** detalhado vive em [`docs/architecture/modular-monolith.md`](../architecture/modular-monolith.md) (seção Naming) e é encarnado pelas skills `create-module`, `create-endpoint`, `pytest-unit`, `pytest-integration` e pelo `pizzaria-reviewer`.

## Consequências

### Positivas

- **Arquivos auto-descritivos.** `user_service.py` é inequívoco em abas, buscas e stack traces, sem depender do diretório pai.
- **Aderência ao estilo NestJS-like** que orienta o projeto, dentro do que o import system do Python permite.
- **Migração mecânica e segura.** `git mv` preserva histórico; mypy + suíte de 78 testes cobrem regressões de import/wiring.

### Negativas / custos

- **Assimetria singular/plural.** Arquivo `user_*` (singular) dentro de `users/` (plural). Documentado explicitamente para evitar dúvida em módulos futuros (`orders/` → `order_service.py`).
- **Reescrita de documentação.** AGENTS.md, guideline de arquitetura, README e 6 skills precisaram ser atualizados para a nova convenção (feito neste mesmo PR).
- **Segunda mudança de convenção em uma semana.** Mitigado por este ADR, que torna a decisão rastreável e fecha o tema (não reintroduzir flat nem dotted).

## Alternativas consideradas

- **Manter flat sem prefixo** (`service.py`): rejeitado pela perda de legibilidade ao navegar arquivos de múltiplos módulos.
- **Dotted estilo NestJS** (`user.service.py`): **inviável** — não importável em Python (verificado empiricamente).
- **camelCase** (`userService.py`): rejeitado por violar PEP 8 (módulos em `snake_case`).

## Referências

- Guideline operacional: [`docs/architecture/modular-monolith.md`](../architecture/modular-monolith.md) (seção Naming)
- ADR base (padrão arquitetural): [`docs/adr/0001-adotar-modular-monolith-em-camadas.md`](0001-adotar-modular-monolith-em-camadas.md)
