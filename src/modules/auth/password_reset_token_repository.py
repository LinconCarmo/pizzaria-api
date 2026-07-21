from datetime import datetime
from typing import Protocol, cast
from uuid import UUID

from prisma import Prisma, types


class PasswordResetTokenRepositoryProtocol(Protocol):
    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> dict[str, object]: ...


class PasswordResetTokenRepository:
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> dict[str, object]:
        data: types.PasswordResetTokenCreateInput = {
            "user": {
                "connect": {
                    "id": str(user_id),
                }
            },
            "tokenHash": token_hash,
            "expiresAt": expires_at,
        }

        created = await self._db.passwordresettoken.create(data=data)

        return cast(dict[str, object], created.model_dump())
