# Pizzaria API

API backend para gerenciamento de usuários, pedidos e produtos de uma pizzaria.

## Tecnologias

- Python
- FastAPI
- Prisma
- MySQL
- Docker
- RabbitMQ
- Redis

---

## Setup do Projeto

### Clonar repositório

```bash
git clone https://github.com/LinconCarmo/pizzaria-api.git
```

---

### Entrar na pasta do projeto

```bash
cd pizzaria-api
```

---

### Configurar variáveis ambiente

Copiar `.env.example` para `.env`.

Linux/macOS:

```bash
cp .env.example .env
```

Windows:

```bash
copy .env.example .env
```

Após copiar, ajuste os valores das variáveis conforme necessário.

---

### Instalar dependências

```bash
uv sync
```

---

## Infraestrutura Local

Subir toda a infraestrutura:

```bash
docker compose up -d
```

Parar infraestrutura:

```bash
docker compose down
```

Ver containers ativos:

```bash
docker ps
```

---

## Serviços Disponíveis

| Serviço | Porta |
|---|---|
| MySQL | 3306 |
| RabbitMQ | 5672 |
| RabbitMQ UI | 15672 |
| Redis | 6379 |

---

## RabbitMQ Management UI

Acesse:

```text
http://localhost:15672
```

Usuário e senha definidos no `.env`.

---

## Estrutura do Projeto

O projeto segue arquitetura modular por feature, inspirada no padrão utilizado no NestJS.

```text
src/
├── core/
├── infra/
├── modules/
│   ├── health/
│   └── users/
├── shared/
├── app.module.py
└── main.py
```

Cada módulo possui sua própria organização interna, contendo:
- controller
- service
- schema
- repository
- tests

Essa abordagem melhora:
- organização
- escalabilidade
- manutenção
- separação de responsabilidades

---

## Executar Aplicação

Iniciar servidor FastAPI em modo desenvolvimento:

```bash
uv run uvicorn src.main:app --reload
```

---

## Documentação da API

Swagger/OpenAPI automático disponível em:

```text
http://127.0.0.1:8000/docs
```