from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from prisma import Prisma, types
from prisma.models import PasswordResetToken


class PasswordResetTokenRepositoryProtocol(Protocol):
    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None: ...

    async def delete_by_user_id(
        self,
        user_id: UUID,
    ) -> None: ...

    async def get_by_token_hash(
        self,
        *,
        token_hash: str,
    ) -> PasswordResetToken | None: ...

    async def mark_as_used(
        self,
        *,
        token_id: UUID,
    ) -> None: ...


class PasswordResetTokenRepository:
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        data: types.PasswordResetTokenCreateInput = {
            "user": {
                "connect": {
                    "id": str(user_id),
                }
            },
            "tokenHash": token_hash,
            "expiresAt": expires_at,
        }

        await self._db.passwordresettoken.create(
            data=data,
        )

    async def delete_by_user_id(
        self,
        user_id: UUID,
    ) -> None:
        await self._db.passwordresettoken.delete_many(
            where={
                "userId": str(user_id),
            }
        )

    async def get_by_token_hash(
        self,
        *,
        token_hash: str,
    ) -> PasswordResetToken | None:
        row = await self._db.passwordresettoken.find_first(where={"tokenHash": token_hash})
        return row

    async def mark_as_used(self, *, token_id: UUID) -> None:
        await self._db.passwordresettoken.update(
            where={"id": str(token_id)}, data={"usedAt": datetime.now(UTC)}
        )
