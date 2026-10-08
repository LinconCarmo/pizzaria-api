# Imagem da API. Migrations e seed não rodam no startup: são o passo de deploy,
# executado com esta mesma imagem antes de subir a API:
#   docker run --rm --env-file .env pizzaria-api ./scripts/db-setup.sh

FROM ghcr.io/astral-sh/uv:0.8.15 AS uv

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

COPY --from=uv /uv /usr/local/bin/uv

# libatomic1: Node que o prisma-client-py baixa para gerar o client.
# openssl: exigido pelos engines do Prisma em runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 openssl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 app

WORKDIR /app
RUN chown app:app /app
USER app

COPY --chown=app:app pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=app:app src ./src
COPY --chown=app:app scripts/db-setup.sh ./scripts/db-setup.sh

# Gera o client Prisma e baixa os engines no cache do usuário `app`.
RUN prisma generate --schema=src/infra/prisma/schema.prisma

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
