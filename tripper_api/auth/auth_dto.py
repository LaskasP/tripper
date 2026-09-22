from pydantic import BaseModel


class AccountResponse(BaseModel):
    email: str
    display_name: str


class SessionResponse(BaseModel):
    account: AccountResponse


class GoogleConfigResponse(BaseModel):
    client_id: str
