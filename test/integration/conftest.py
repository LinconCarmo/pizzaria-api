import os
import subprocess
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from prisma import Prisma
from testcontainers.mysql import MySqlContainer

from src.core.rate_limit import rate_limiter
from src.infra.email.email_service import EmailServiceProtocol
from src.infra.seed import DEFAULT_UNIT
from src.infra.seed import seed_roles as seed_default_roles
from src.infra.seed import seed_unit as seed_default_unit


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

    client = Prisma(
        datasource={"url": db_url},
        use_dotenv=False,
    )

    await client.connect()

    try:
        yield client
    finally:
        await client.disconnect()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def seed_roles(db: Prisma) -> None:
    await seed_default_roles(db)
    await seed_default_unit(db)


@pytest_asyncio.fixture(autouse=True)
async def clean_database(db: Prisma) -> AsyncGenerator[None]:
    rate_limiter.clear()

    yield

    await db.user.delete_many()

    await db.unit.delete_many(
        where={"cnpj": {"not": DEFAULT_UNIT["cnpj"]}},
    )


class FakeEmailService(EmailServiceProtocol):
    """E-mail sempre disponível nos testes; guarda o que seria enviado."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def is_available(self) -> bool:
        return True

    async def send_password_reset_email(self, email: str, token: str) -> None:
        self.sent.append((email, token))


@pytest_asyncio.fixture(scope="session")
async def client(db: Prisma) -> AsyncGenerator[AsyncClient]:
    from src.infra.database import get_db
    from src.infra.email.email_dependencies import get_email_service
    from src.main import app

    def _override_db() -> Prisma:
        return db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_email_service] = FakeEmailService

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
