#!/bin/sh
# Passo de deploy do banco: aplica migrations pendentes e semeia roles/unidade
# (idempotente). Mesmo efeito de `poe db-setup`, sem depender do poe/uv.
set -eu

prisma migrate deploy --schema=src/infra/prisma/schema.prisma
python -m src.infra.seed
