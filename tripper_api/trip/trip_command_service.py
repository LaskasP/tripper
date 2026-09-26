from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.destination.destination_errors import (
    TripDestinationInUseError,
    TripDestinationMismatchError,
)
from tripper_api.destination.destination_model import Destination
from tripper_api.destination.destination_repository import DestinationRepository
from tripper_api.itinerary.itinerary_repository import ItineraryRepository
from tripper_api.membership.membership_dto import TripSummaryResponse
from tripper_api.membership.membership_model import TripMembership, TripRole
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_access_control import TripAccessControl
from tripper_api.trip.trip_command_dto import (
    TripCreateRequest,
    TripDetailsUpdateRequest,
)
from tripper_api.trip.trip_command_errors import (
    TripDateRangeExcludesPlansError,
    TripRevisionConflictError,
)
from tripper_api.trip.trip_guide_dto import TripDetailResponse
from tripper_api.trip.trip_guide_reader import TripGuideReader
from tripper_api.trip.trip_model import Trip
from tripper_api.trip.trip_repository import TripRepository


class TripCommandService:
    def __init__(
        self,
        session: AsyncSession,
        trip_repository: TripRepository,
        destination_repository: DestinationRepository,
        membership_repository: MembershipRepository,
        access_control: TripAccessControl,
        itinerary_repository: ItineraryRepository,
        guide_reader: TripGuideReader,
    ) -> None:
        self._session = session
        self._trip_repository = trip_repository
        self._destination_repository = destination_repository
        self._membership_repository = membership_repository
        self._access_control = access_control
        self._itinerary_repository = itinerary_repository
        self._guide_reader = guide_reader

    async def create(
        self,
        *,
        account_id: UUID,
        request: TripCreateRequest,
    ) -> TripSummaryResponse:
        trip = Trip(
            id=uuid4(),
            name=request.name,
            short_name=request.short_name,
            description=request.description,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        destination = Destination(
            id=uuid4(),
            trip_id=trip.id,
            name=request.destination,
            timezone=request.timezone,
            latitude=request.location.lat if request.location is not None else None,
            longitude=request.location.lng if request.location is not None else None,
            position=0,
        )
        membership = TripMembership(
            id=uuid4(),
            trip_id=trip.id,
            account_id=account_id,
            role=TripRole.CREATOR,
        )
        async with self._session.begin():
            await self._trip_repository.add_trip(trip)
            await self._destination_repository.add(destination)
            await self._membership_repository.add(membership)
        return TripSummaryResponse(
            id=trip.id,
            name=trip.name,
            destination=destination.name,
            short_name=trip.short_name,
            start_date=trip.start_date,
            end_date=trip.end_date,
            role=membership.role,
        )

    async def update_details(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        request: TripDetailsUpdateRequest,
    ) -> TripDetailResponse:
        revision_conflict = False
        async with self._session.begin():
            access = await self._access_control.lock_for_edit(trip_id, account_id)
            if access.trip.revision != request.starting_revision:
                revision_conflict = True
            else:
                destinations = await self._destination_repository.list_for_update(
                    trip_id
                )
                itinerary = await self._itinerary_repository.trip_references(trip_id)
                if any(
                    plan_date < request.start_date or plan_date > request.end_date
                    for plan_date in itinerary.plan_dates
                ):
                    raise TripDateRangeExcludesPlansError

                existing_by_id = {
                    destination.id: destination for destination in destinations
                }
                requested_ids = {
                    destination.id
                    for destination in request.destinations
                    if destination.id is not None
                }
                if not requested_ids.issubset(existing_by_id):
                    raise TripDestinationMismatchError
                removed = [
                    destination
                    for destination in destinations
                    if destination.id not in requested_ids
                ]
                if any(
                    destination.id in itinerary.destination_ids
                    for destination in removed
                ):
                    raise TripDestinationInUseError

                access.trip.name = request.name
                access.trip.short_name = request.short_name
                access.trip.description = request.description
                access.trip.start_date = request.start_date
                access.trip.end_date = request.end_date
                access.trip.revision += 1
                access.trip.content_revision += 1

                updated_destinations: list[Destination] = []
                for position, item in enumerate(request.destinations):
                    if item.id is None:
                        destination = Destination(
                            id=uuid4(),
                            trip_id=trip_id,
                            name=item.name,
                            timezone=item.timezone,
                            latitude=(item.location.lat if item.location else None),
                            longitude=(item.location.lng if item.location else None),
                            position=position,
                        )
                    else:
                        destination = existing_by_id[item.id]
                        destination.name = item.name
                        destination.timezone = item.timezone
                        destination.latitude = (
                            item.location.lat if item.location else None
                        )
                        destination.longitude = (
                            item.location.lng if item.location else None
                        )
                        destination.revision += 1
                    updated_destinations.append(destination)
                await self._destination_repository.replace(
                    previous=destinations,
                    current=updated_destinations,
                    removed=removed,
                )
        if revision_conflict:
            latest_values = await self._guide_reader.get_participant_guide(
                trip_id, account_id
            )
            raise TripRevisionConflictError(latest_values.model_dump(mode="json"))
        return await self._guide_reader.get_participant_guide(trip_id, account_id)
