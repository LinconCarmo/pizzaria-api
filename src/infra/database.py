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
    logger.info("Connected to database")
    logger.bind(host=settings.host, port=settings.port).info("server_started")
    await seed_roles(db)

    yield

    await db.disconnect()
    logger.info("Disconnected from database")
