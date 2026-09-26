import pytest
from pydantic import ValidationError

from tripper_api.core.config import Settings

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
