from pydantic import BaseModel, ConfigDict


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class AccountResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda name: _to_camel(name), populate_by_name=True
    )

    email: str
    display_name: str


class SessionResponse(BaseModel):
    account: AccountResponse


class GoogleConfigResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda name: _to_camel(name), populate_by_name=True
    )

    client_id: str
