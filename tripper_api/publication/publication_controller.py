from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.publication.publication_dependencies import get_publication_service
from tripper_api.publication.publication_dto import (
    PublicationChangeRequest,
    PublicationResponse,
)
from tripper_api.publication.publication_service import PublicationService
from tripper_api.trip.trip_dependencies import get_trip_guide_reader
from tripper_api.trip.trip_guide_dto import PublicTripGuideResponse
from tripper_api.trip.trip_guide_reader import TripGuideReader

router = APIRouter(prefix="/api")


@router.get("/trips/{trip_id}/publication", response_model=PublicationResponse)
async def get_publication(
    trip_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[PublicationService, Depends(get_publication_service)],
) -> PublicationResponse:
    return await service.get(trip_id, user.id)


@router.post("/trips/{trip_id}/publication", response_model=PublicationResponse)
async def publish_trip(
    trip_id: UUID,
    request: PublicationChangeRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[PublicationService, Depends(get_publication_service)],
) -> PublicationResponse:
    return await service.publish(trip_id, user.id, request.starting_revision)


@router.delete("/trips/{trip_id}/publication", response_model=PublicationResponse)
async def unpublish_trip(
    trip_id: UUID,
    request: PublicationChangeRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[PublicationService, Depends(get_publication_service)],
) -> PublicationResponse:
    return await service.unpublish(trip_id, user.id, request.starting_revision)


@router.post("/trips/{trip_id}/publication/rotate", response_model=PublicationResponse)
async def rotate_public_link(
    trip_id: UUID,
    request: PublicationChangeRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[PublicationService, Depends(get_publication_service)],
) -> PublicationResponse:
    return await service.rotate(trip_id, user.id, request.starting_revision)


@router.get("/public-guides/{public_token}", response_model=PublicTripGuideResponse)
async def get_public_guide(
    public_token: str,
    reader: Annotated[TripGuideReader, Depends(get_trip_guide_reader)],
) -> PublicTripGuideResponse:
    return await reader.get_public_guide(public_token)
