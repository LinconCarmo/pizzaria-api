import asyncio

from prisma import Prisma, types

from src.core.logger import logger

# (name, description) — `name` deve casar com `UserRole` (src/modules/users/user_schema.py).
ROLES: list[tuple[str, str]] = [
    ("CUSTOMER", "Cliente"),
    ("STAFF", "Funcionário"),
    ("ADMIN", "Administrador"),
]

DEFAULT_UNIT: types.UnitCreateInput = {
    "name": "Unidade Principal",
    "cnpj": "12345678000195",
    "email": "contato@pizzaria.com",
    "phone": "41999999999",
    "street": "Rua Principal",
    "number": "100",
    "neighborhood": "Centro",
    "city": "Curitiba",
    "state": "PR",
    "zip": "80000000",
}


async def seed_roles(db: Prisma) -> None:
    """Garante (idempotente) que os roles padrão existem.

    `create`/`update` em ``UserRepository`` conectam o role por ``name``, então o
    primeiro ``POST /users`` falha se a tabela ``roles`` estiver vazia. Roda como
    passo de deploy (``poe db-setup`` ou ``poe prisma-seed``), não no startup.
    """
    for name, description in ROLES:
        where: types.RoleWhereUniqueInput = {"name": name}
        data: types.RoleUpsertInput = {
            "create": {"name": name, "description": description},
            "update": {},
        }
        await db.role.upsert(where=where, data=data)

    logger.bind(roles=[name for name, _ in ROLES]).info("roles_seeded")


async def find_missing_roles(db: Prisma) -> list[str]:
    """Só leitura: devolve os roles padrão que ainda não existem no banco."""
    expected = [name for name, _ in ROLES]
    where: types.RoleWhereInput = {"name": {"in": expected}}
    existing = {role.name for role in await db.role.find_many(where=where)}
    return [name for name in expected if name not in existing]


async def seed_unit(db: Prisma) -> None:
    """Garante (idempotente) que a unidade padrão existe."""

    where: types.UnitWhereUniqueInput = {
        "cnpj": DEFAULT_UNIT["cnpj"],
    }

    data: types.UnitUpsertInput = {
        "create": DEFAULT_UNIT,
        "update": {},
    }

    await db.unit.upsert(where=where, data=data)

    logger.bind(unit=DEFAULT_UNIT["name"]).info("unit_seeded")


async def main() -> None:
    db = Prisma()
    await db.connect()
    try:
        await seed_roles(db)
        await seed_unit(db)
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
