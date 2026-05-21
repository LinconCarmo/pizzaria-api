# ADR 0001 — Adotar Modular Monolith em Camadas

- **Status:** Aceito
- **Data:** 2026-05-20
- **Autor:** Martin Morães
- **Supersede:** —
- **Superseded by:** —

## Contexto

O `pizzaria-api` é um backend Python (FastAPI + Prisma + MySQL) que tende a crescer em escopo: catálogo, pedidos, pagamentos, entrega, fidelidade. Sem uma estratégia explícita de organização, o sistema corre dois riscos previsíveis:

1. **Acoplamento implícito.** Python não tem `private`/`internal` reais. Sem disciplina e fronteiras explícitas, qualquer arquivo passa a importar diretamente entidades, repositórios e detalhes internos de qualquer outro — produzindo o clássico "big ball of mud" onde refatorar uma área significa caçar imports pelo projeto inteiro.
2. **Custo prematuro de microsserviços.** Quebrar o sistema em serviços agora adicionaria complexidade operacional (deploy, observabilidade, contrato de rede, consistência distribuída) que o time e o domínio ainda não demandam.

Precisamos de um padrão que permita evolução modular sem pagar o custo de distribuição, e que seja simples o suficiente para o estágio atual do projeto.

## Decisão

Adotamos **Modular Monolith em Camadas (layout flat por módulo)** como padrão arquitetural do `pizzaria-api`.

Em resumo:

- Código fica em `src/modules/<feature>/`, **um pacote por bounded context**.
- Cada módulo tem **7 arquivos em layout flat** (sem subpastas):
  - `__init__.py`, `router.py`, `controller.py`, `service.py`, `repository.py`, `schema.py`, `dependencies.py`.
- **Direção de dependência interna**: `controller → service → repository`. Schema é transversal.
- **Repository é o único arquivo que importa Prisma**; service depende de `<X>RepositoryProtocol`.
- **Comunicação entre módulos** via `Protocol` importado do módulo dono (chamada direta tipada), RabbitMQ (assíncrono) ou cache via Redis.
- **Pydantic v2** para DTOs com Request e Response **sempre separados**; Money é `Decimal`.
- **Erros de domínio** via hierarquia `DomainError` em `src/core/exceptions.py`; service lança, controller nunca captura, handlers globais traduzem para HTTP.
- **DI manual** com `Depends` do FastAPI no `dependencies.py` de cada módulo; sem framework de DI externo; sem `@staticmethod`.
- **Persistência**: Prisma + MySQL, schema único em `src/infra/prisma/schema.prisma`.
- **Testes** em dois níveis: unit (mocks via `spec=`) e integration (Prisma + MySQL real com marker `@pytest.mark.integration`).

O **como** detalhado (estrutura completa, templates, naming, armadilhas) vive em [`docs/architecture/modular-monolith.md`](../architecture/modular-monolith.md) como guia vivo e é encarnado pelas skills `create-module`, `create-endpoint`, `pydantic-schema`, `pytest-unit`, `pytest-integration` e pelos agents `fastapi-architect`, `pizzaria-reviewer`.

Este ADR registra a **decisão** de adotar o padrão; o guideline e as skills podem ser atualizados sem novo ADR enquanto a decisão de fundo permanecer válida.

## Consequências

### Positivas

- **Estrutura previsível.** Arquivo novo tem lugar óbvio; endpoint novo segue o mesmo fluxo dos anteriores. Onboarding fica mais rápido.
- **Domínio testável.** Service depende de `Protocol`, não de Prisma. Testes unitários rodam sem banco, instantâneos.
- **Caminho de evolução claro.** Se um módulo precisar virar serviço futuramente, ele já tem fronteira de tipos e Repository isolando o I/O. A extração vira mecânica, não reescrita.
- **Automação alinhada.** Skills e agents implementam o padrão diretamente — código novo nasce aderente sem cerimônia adicional.
- **Sem overhead de framework de DI.** `Depends` do FastAPI cobre o caso atual com zero dependência extra.

### Negativas / custos

- **Disciplina, não imposição automática.** O padrão depende de code review (e do agent `pizzaria-reviewer`) para detectar violações. Não há `import-linter` ou equivalente — quebrar a fronteira "service importa Prisma" é tecnicamente possível. Pode ser endereçado num ADR futuro.
- **Boilerplate para módulos pequenos.** Mesmo um módulo trivial exige 7 arquivos. Mitigado pela skill `create-module` que faz scaffold.
- **Convenção dupla temporária.** [src/modules/users/](../../src/modules/users/) usa naming legado (`users.module.py`). Convive com o padrão novo até ser migrado; documentado como exceção conhecida.
- **`shared/` precisa de vigilância.** Conhecida tentação de virar lixeira; mitigado pela regra "na dúvida, duplique" e revisão explícita no `pizzaria-reviewer`.

## Alternativas consideradas

- **Layered Monolith não-modular** (uma única árvore `controllers/services/repositories/` para o sistema inteiro): mais simples no início, mas sem fronteiras entre bounded contexts. Rejeitado por ser exatamente o cenário que produz o acoplamento que queremos evitar.
- **Microsserviços desde o início**: rejeitado por adicionar custo operacional desproporcional ao estágio atual.
- **DDD layered "puro" com `domain/application/adapters/infrastructure/` por módulo desde o dia um**: rejeitado por over-engineering para o domínio atual. Mantido como [roadmap aspiracional](../architecture/modular-monolith.md#11-roadmap-aspiracional); será reavaliado quando algum módulo crescer a ponto de exigir entidades imutáveis com invariantes, eventos de domínio in-process ou fronteiras impostas por `import-linter`.

## Referências

- Guideline operacional: [`docs/architecture/modular-monolith.md`](../architecture/modular-monolith.md)
- Skill de scaffold: [`.claude/skills/create-module/SKILL.md`](../../.claude/skills/create-module/SKILL.md)
- Agent de revisão: [`.claude/agents/pizzaria-reviewer.md`](../../.claude/agents/pizzaria-reviewer.md)
