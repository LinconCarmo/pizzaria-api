from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from prisma import Prisma, types


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
    ) -> dict[str, object] | None: ...

    async def reset_password(
        self,
        *,
        user_id: UUID,
        token_id: UUID,
        hashed_password: str,
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
    ) -> dict[str, object] | None:
        where: types.PasswordResetTokenWhereInput = {"tokenHash": token_hash}
        row = await self._db.passwordresettoken.find_first(where=where)
        return row.model_dump() if row is not None else None

    async def reset_password(
        self,
        *,
        user_id: UUID,
        token_id: UUID,
        hashed_password: str,
    ) -> None:
        user_where: types.UserWhereUniqueInput = {
            "id": str(user_id),
        }

        user_data: types.UserUpdateInput = {
            "hashedPassword": hashed_password,
        }

        token_where: types.PasswordResetTokenWhereUniqueInput = {
            "id": str(token_id),
        }

        token_data: types.PasswordResetTokenUpdateInput = {
            "usedAt": datetime.now(UTC),
        }

        async with self._db.tx() as tx:
            await tx.user.update(
                where=user_where,
                data=user_data,
            )

            await tx.passwordresettoken.update(
                where=token_where,
                data=token_data,
            )
