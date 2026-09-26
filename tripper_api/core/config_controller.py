from typing import cast

from fastapi import APIRouter, Request

from tripper_api.core.config import Settings
from tripper_api.core.config_dto import ApplicationConfigResponse

router = APIRouter(prefix="/api/config", tags=["configuration"])


@router.get("", response_model=ApplicationConfigResponse)
async def application_config(request: Request) -> ApplicationConfigResponse:
    settings = cast(Settings, request.app.state.settings)
    return ApplicationConfigResponse(
        invitations_enabled=settings.invitations_enabled,
    )
