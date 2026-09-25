from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _https_url(value: str) -> str:
    stripped = value.strip()
    parsed = urlparse(stripped)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or any(character.isspace() for character in stripped)
    ):
        raise ValueError("url must be an HTTPS URL")
    return stripped


class PhotoCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)
    url: str
    caption: str = ""

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _https_url(value)


class PhotoDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)


class PhotoReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)
    photo_ids: list[UUID]

    @field_validator("photo_ids")
    @classmethod
    def validate_unique_photo_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("photo_ids must be unique")
        return value
