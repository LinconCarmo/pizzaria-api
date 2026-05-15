# Pizzaria API

API backend para gerenciamento de usuários, pedidos e produtos de uma pizzaria.

## Tecnologias

- Python 3.13.1
- FastAPI
- Prisma
- MySQL
- Docker
- RabbitMQ
- Redis

---

## Requisitos

- Python 3.13.1
- Docker
- uv

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

### Instalar Python 3.13.1

```bash
uv python install 3.13.1
```

---

### Configurar variáveis ambiente

Copiar `.env.example` para `.env`.

Windows:

```bash
copy .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

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

---

## Executar Aplicação

```bash
uv run uvicorn src.main:app --reload
```

---

## Verificar versão do Python

```bash
uv run python --version
```

---

## Documentação da API

Swagger/OpenAPI automático disponível em:

```text
http://127.0.0.1:8000/docs
```


## Variáveis de Ambiente

As configurações da aplicação são centralizadas via Pydantic Settings (`src/core/config.py`).

Exemplo de variáveis utilizadas:

```env
DATABASE_URL=mysql://root:root@localhost:3306/pizzaria
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://guest:guest@localhost:5672
JWT_SECRET=change_me
APP_ENV=development
LOG_LEVEL=debug
```