from pydantic import BaseModel


class ApplicationConfigResponse(BaseModel):
    invitations_enabled: bool
