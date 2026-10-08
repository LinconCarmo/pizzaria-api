from datetime import UTC, datetime, timedelta
from uuid import UUID

DEFAULT_RESET_TOKEN_ID = UUID("00000000-0000-4000-8000-0000000000a1")
DEFAULT_RESET_TOKEN_USER_ID = UUID("00000000-0000-4000-8000-000000000001")


def make_password_reset_token_row(
    *,
    id: UUID = DEFAULT_RESET_TOKEN_ID,
    user_id: UUID = DEFAULT_RESET_TOKEN_USER_ID,
    token_hash: str = "token-hash",
    expires_at: datetime | None = None,
    used_at: datetime | None = None,
) -> dict[str, object]:
    return {
        "id": str(id),
        "userId": str(user_id),
        "tokenHash": token_hash,
        "expiresAt": expires_at or datetime.now(UTC) + timedelta(hours=1),
        "usedAt": used_at,
        "createdAt": datetime.now(UTC),
    }
