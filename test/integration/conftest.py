import os
import subprocess
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from prisma import Prisma
from testcontainers.mysql import MySqlContainer


@pytest.fixture(scope="session")
def mysql_container() -> MySqlContainer:
    with MySqlContainer("mysql:8.0") as mysql:
        yield mysql


@pytest_asyncio.fixture(scope="session")
async def db(mysql_container: MySqlContainer) -> AsyncGenerator[Prisma]:
    raw_url = mysql_container.get_connection_url()
    db_url = raw_url.replace("mysql+pymysql://", "mysql://")
    os.environ["DATABASE_URL"] = db_url

    subprocess.run(
        [
            "uv",
            "run",
            "prisma",
            "migrate",
            "deploy",
            "--schema=src/infra/prisma/schema.prisma",
        ],
        check=True,
        env={**os.environ, "DATABASE_URL": db_url},
    )
    client = Prisma(datasource={"url": db_url}, use_dotenv=False)
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()


ROLES = [
    ("CUSTOMER", "Cliente"),
    ("STAFF", "Funcionário"),
    ("ADMIN", "Administrador"),
]


@pytest_asyncio.fixture(scope="session", autouse=True)
async def seed_roles(db: Prisma) -> None:
    for name, description in ROLES:
        await db.role.upsert(
            where={"name": name},
            data={
                "create": {"name": name, "description": description},
                "update": {},
            },
        )


@pytest_asyncio.fixture(autouse=True)
async def clean_database(db: Prisma) -> AsyncGenerator[None]:
    yield
    await db.user.delete_many()


@pytest_asyncio.fixture(scope="session")
async def client(db: Prisma) -> AsyncGenerator[AsyncClient]:
    from src.infra.database import get_db
    from src.main import app

    def _override_db() -> Prisma:
        return db

    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
