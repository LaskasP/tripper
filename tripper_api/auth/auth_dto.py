from uuid import UUID

from pydantic import BaseModel


class AccountResponse(BaseModel):
    id: UUID
    email: str
    display_name: str


class SessionResponse(BaseModel):
    account: AccountResponse


class GoogleConfigResponse(BaseModel):
    client_id: str
