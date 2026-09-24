from datetime import date
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DailyPlanWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    starting_revision: int = Field(ge=1)
    destination_id: UUID
    title: str = Field(max_length=200)
    summary: str = ""
    background_image: str = ""

    @field_validator("background_image")
    @classmethod
    def validate_background_image(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if value and (parsed.scheme != "https" or not parsed.netloc):
            raise ValueError("background_image must be an HTTPS URL")
        return value


class DailyPlanRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)


class DailyPlanMoveRequest(DailyPlanRevisionRequest):
    target_date: date


class DailyPlanResponse(BaseModel):
    id: UUID
    destination_id: UUID
    revision: int
    date: date
    title: str
    summary: str
    background_image: str
