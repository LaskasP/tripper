from base64 import urlsafe_b64decode

from pydantic import SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TRIPPER_",
        extra="ignore",
    )

    database_url: str
    google_client_id: str = "google_client_id_not_set"
    database_echo: bool = False
    invitations_enabled: bool = True
    invitation_token_key: SecretStr | None = None
    invitation_base_url: str = "http://localhost:8080/tripper/invitations"
    mailgun_api_key: SecretStr | None = None
    mailgun_domain: str | None = None
    invitation_from_email: str | None = None
    mailgun_webhook_signing_key: SecretStr | None = None

    @field_validator("database_url")
    @classmethod
    def require_async_psycopg(cls, value: str) -> str:
        expected_scheme = "postgresql+psycopg_async://"
        if not value.startswith(expected_scheme):
            raise ValueError(f"database URL must start with {expected_scheme}")
        return value

    @field_validator("invitation_token_key", mode="before")
    @classmethod
    def normalize_invitation_token_key(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator(
        "mailgun_api_key",
        "mailgun_domain",
        "invitation_from_email",
        "mailgun_webhook_signing_key",
        mode="before",
    )
    @classmethod
    def normalize_optional_invitation_setting(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("invitation_token_key")
    @classmethod
    def require_valid_invitation_token_key(
        cls, value: SecretStr | None, info: ValidationInfo
    ) -> SecretStr | None:
        if value is None or info.data.get("invitations_enabled") is False:
            return None
        key = urlsafe_b64decode(value.get_secret_value().encode())
        if len(key) != 32:
            raise ValueError("invitation token key must contain 32 bytes")
        return value

    @model_validator(mode="after")
    def require_invitation_token_key_when_enabled(self) -> "Settings":
        if self.invitations_enabled and self.invitation_token_key is None:
            raise ValueError(
                "invitation token key is required when invitations are enabled"
            )
        return self

    def invitation_key_bytes(self) -> bytes:
        if not self.invitations_enabled or self.invitation_token_key is None:
            raise RuntimeError("invitations are disabled")
        return urlsafe_b64decode(self.invitation_token_key.get_secret_value().encode())
