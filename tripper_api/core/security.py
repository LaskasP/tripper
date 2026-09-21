from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID


def require_current_user() -> AuthenticatedUser:
    """Authentication boundary to be supplied by the chosen sign-in integration."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )
