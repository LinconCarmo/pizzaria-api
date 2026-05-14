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

## Estrutura

Projeto organizado em arquitetura modular por feature.

## Executar API

```bash
python src/main.py
```

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

## Serviços Disponíveis

| Serviço | Porta |
|---|---|
| MySQL | 3306 |
| RabbitMQ | 5672 |
| RabbitMQ UI | 15672 |
| Redis | 6379 |

## RabbitMQ Management UI

Acesse:

```text
http://localhost:15672
```

Usuário e senha definidos no `.env`.