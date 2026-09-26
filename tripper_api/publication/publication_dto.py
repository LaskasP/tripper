from pydantic import BaseModel, ConfigDict, Field


class PublicationChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)


class PublicationResponse(BaseModel):
    is_published: bool
    public_token: str | None
    revision: int
