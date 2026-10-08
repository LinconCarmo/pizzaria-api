from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prisma import Prisma

from src.core.config import settings
from src.core.logger import logger
from src.infra.seed import seed_roles

db = Prisma()


def get_db() -> Prisma:
    return db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await db.connect()
    logger.info("database_connected")
    try:
        await seed_roles(db)
        logger.bind(host=settings.host, port=settings.port).info("server_started")

        yield
    finally:
        await db.disconnect()
        logger.info("database_disconnected")
