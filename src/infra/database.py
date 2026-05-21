from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prisma import Prisma

from src.core.logger import logger

db = Prisma()


def get_db() -> Prisma:
    return db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await db.connect()
    logger.info("Connected to database")

    yield

    await db.disconnect()
    logger.info("Disconnected from database")
