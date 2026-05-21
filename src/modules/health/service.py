from src.infra.database import db
from src.infra.redis_client import ping_redis


class HealthService:
    @staticmethod
    async def check():
        checks = {}

        try:
            await db.query_raw("SELECT 1")
            checks["db"] = "ok"
        except Exception:
            checks["db"] = "failed"

        try:
            await ping_redis()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "failed"

        status = "ok"

        if "failed" in checks.values():
            status = "error"

        return {
            "status": status,
            "checks": checks,
        }
