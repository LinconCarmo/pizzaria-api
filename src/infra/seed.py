import asyncio

from prisma import Prisma, types

from src.core.logger import logger

# (name, description) — `name` deve casar com `UserRole` (src/modules/users/user_schema.py).
ROLES: list[tuple[str, str]] = [
    ("CUSTOMER", "Cliente"),
    ("STAFF", "Funcionário"),
    ("ADMIN", "Administrador"),
]


async def seed_roles(db: Prisma) -> None:
    """Garante (idempotente) que os roles padrão existem.

    `create`/`update` em ``UserRepository`` conectam o role por ``name``, então o
    primeiro ``POST /users`` falha se a tabela ``roles`` estiver vazia. Roda no
    startup (``lifespan``) e via ``poe prisma-seed``.
    """
    for name, description in ROLES:
        where: types.RoleWhereUniqueInput = {"name": name}
        data: types.RoleUpsertInput = {
            "create": {"name": name, "description": description},
            "update": {},
        }
        await db.role.upsert(where=where, data=data)

    logger.bind(roles=[name for name, _ in ROLES]).info("roles_seeded")


async def main() -> None:
    db = Prisma()
    await db.connect()
    try:
        await seed_roles(db)
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
