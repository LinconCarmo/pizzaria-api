SCHEMA = src/infra/prisma/schema.prisma

.PHONY: dev prisma-migration-run prisma-generate test

dev:
	uv run uvicorn src.main:app --reload

prisma-migration-run:
	uv run prisma migrate dev --schema=$(SCHEMA)

prisma-generate:
	uv run prisma generate --schema=$(SCHEMA)

test:
	uv run pytest