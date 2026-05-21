import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from prisma import Prisma

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(scope="session")
async def db() -> AsyncGenerator[Prisma]:
    test_db_url = os.environ.get("DATABASE_URL_TEST") or os.environ.get("DATABASE_URL")
    if test_db_url is None:
        pytest.skip("DATABASE_URL/DATABASE_URL_TEST not set — skipping integration tests")
    os.environ["DATABASE_URL"] = test_db_url

    client = Prisma()
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(db: Prisma) -> AsyncGenerator[None]:
    await db.user.delete_many()
    yield
    await db.user.delete_many()


@pytest_asyncio.fixture
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
