from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from prisma import Prisma
from prisma.actions import PasswordResetTokenActions, UserActions
from prisma.models import PasswordResetToken

from src.modules.auth.password_reset_token_repository import PasswordResetTokenRepository
from test.factories import make_password_reset_token_row

USER_ID = UUID("00000000-0000-4000-8000-000000000001")
TOKEN_ID = UUID("00000000-0000-4000-8000-0000000000a1")
TOKEN_HASH = "token-hash"
NEW_HASH = "new-password-hash"


@pytest.fixture
def tokens() -> AsyncMock:
    return AsyncMock(spec=PasswordResetTokenActions)


@pytest.fixture
def db(tokens: AsyncMock) -> AsyncMock:
    mock = AsyncMock(spec=Prisma)
    mock.passwordresettoken = tokens
    return mock


@pytest.fixture
def repository(db: AsyncMock) -> PasswordResetTokenRepository:
    return PasswordResetTokenRepository(db)


async def test_create_connects_user_and_stores_hash(
    repository: PasswordResetTokenRepository, tokens: AsyncMock
) -> None:
    expires_at = datetime.now(UTC) + timedelta(hours=1)

    await repository.create(user_id=USER_ID, token_hash=TOKEN_HASH, expires_at=expires_at)

    data = tokens.create.call_args.kwargs["data"]
    assert data["user"] == {"connect": {"id": str(USER_ID)}}
    assert data["tokenHash"] == TOKEN_HASH
    assert data["expiresAt"] == expires_at


async def test_delete_by_user_id_removes_every_token_of_user(
    repository: PasswordResetTokenRepository, tokens: AsyncMock
) -> None:
    await repository.delete_by_user_id(USER_ID)

    tokens.delete_many.assert_awaited_once_with(where={"userId": str(USER_ID)})


async def test_get_by_token_hash_returns_row_when_found(
    repository: PasswordResetTokenRepository, tokens: AsyncMock
) -> None:
    row = MagicMock(spec=PasswordResetToken)
    row.model_dump.return_value = make_password_reset_token_row(token_hash=TOKEN_HASH)
    tokens.find_first.return_value = row

    result = await repository.get_by_token_hash(token_hash=TOKEN_HASH)

    assert result is not None
    assert result["tokenHash"] == TOKEN_HASH


async def test_get_by_token_hash_returns_none_when_missing(
    repository: PasswordResetTokenRepository, tokens: AsyncMock
) -> None:
    tokens.find_first.return_value = None

    assert await repository.get_by_token_hash(token_hash=TOKEN_HASH) is None


async def test_reset_password_updates_user_and_marks_token_used_in_one_transaction(
    repository: PasswordResetTokenRepository, db: AsyncMock
) -> None:
    tx = AsyncMock(spec=Prisma)
    tx.user = AsyncMock(spec=UserActions)
    tx.passwordresettoken = AsyncMock(spec=PasswordResetTokenActions)
    db.tx.return_value.__aenter__.return_value = tx

    await repository.reset_password(user_id=USER_ID, token_id=TOKEN_ID, hashed_password=NEW_HASH)

    tx.user.update.assert_awaited_once_with(
        where={"id": str(USER_ID)}, data={"hashedPassword": NEW_HASH}
    )
    token_update = tx.passwordresettoken.update.call_args.kwargs
    assert token_update["where"] == {"id": str(TOKEN_ID)}
    assert token_update["data"]["usedAt"] is not None
