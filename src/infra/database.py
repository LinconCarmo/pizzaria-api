from contextlib import asynccontextmanager

from prisma import Prisma

from src.core.logger import logger

db = Prisma()


async def get_db():
    return db


@asynccontextmanager
async def lifespan(app):
    await db.connect()

    logger.info("Connected to database")

    yield

    await db.disconnect()

    logger.info("Disconnected from database")