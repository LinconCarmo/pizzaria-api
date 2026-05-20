SCHEMA = src/infra/prisma/schema.prisma

.PHONY: prisma-migration-run prisma-generate

prisma-migration-run:
	uv run prisma migrate dev --schema=$(SCHEMA)

prisma-generate:
	uv run prisma generate --schema=$(SCHEMA)
