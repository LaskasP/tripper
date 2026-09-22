from pydantic import field_validator
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

    @field_validator("database_url")
    @classmethod
    def require_async_psycopg(cls, value: str) -> str:
        expected_scheme = "postgresql+psycopg_async://"
        if not value.startswith(expected_scheme):
            raise ValueError(f"database URL must start with {expected_scheme}")
        return value
