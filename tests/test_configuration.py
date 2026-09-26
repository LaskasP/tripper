import pytest
from pydantic import ValidationError

from tripper_api.core.config import Settings
from tripper_api.invitation.invitation_worker_main import run as run_invitation_worker

INVITATION_KEY = "--GlAsI7zn2JODd7UGI2F-oaV8iSIoNlxyMGtGSshps="


def test_settings_accept_the_async_psycopg_postgresql_driver() -> None:
    settings = Settings(
        database_url="postgresql+psycopg_async://tripper:secret@localhost/tripper",
        google_client_id="test-client-id",
        invitation_token_key=INVITATION_KEY,
    )

    assert settings.database_url.startswith("postgresql+psycopg_async://")


def test_settings_reject_sqlite() -> None:
    with pytest.raises(ValidationError, match=r"postgresql\+psycopg_async"):
        Settings(
            database_url="sqlite:///tripper.db",
            google_client_id="test-client-id",
            invitation_token_key=INVITATION_KEY,
        )


def test_disabled_invitations_do_not_require_invitation_secrets() -> None:
    settings = Settings(
        database_url="postgresql+psycopg_async://tripper:secret@localhost/tripper",
        invitations_enabled=False,
    )

    assert settings.invitations_enabled is False
    assert settings.invitation_token_key is None


@pytest.mark.asyncio
async def test_disabled_invitation_worker_exits_without_delivery_settings() -> None:
    settings = Settings(
        database_url="postgresql+psycopg_async://tripper:secret@localhost/tripper",
        invitations_enabled=False,
    )

    await run_invitation_worker(settings)
