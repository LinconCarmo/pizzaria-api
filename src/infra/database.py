from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prisma import Prisma

from src.core.config import settings
from src.core.logger import logger
from src.infra.email.email_dependencies import warn_if_email_disabled
from src.infra.seed import find_missing_roles

db = Prisma()


def get_db() -> Prisma:
    return db


async def warn_if_roles_missing(client: Prisma) -> None:
    """O seed é passo de deploy; aqui o startup só avisa se ele não rodou."""
    missing = await find_missing_roles(client)
    if missing:
        logger.bind(missing=missing, fix="poe db-setup").warning("roles_not_seeded")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await db.connect()
    logger.info("database_connected")
    try:
        await warn_if_roles_missing(db)
        warn_if_email_disabled()
        logger.bind(host=settings.host, port=settings.port).info("server_started")

        yield
    finally:
        await db.disconnect()
        logger.info("database_disconnected")
