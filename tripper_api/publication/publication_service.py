import asyncio
from datetime import UTC, datetime
from secrets import token_urlsafe
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.membership.membership_model import TripRole
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.publication.publication_dto import PublicationResponse
from tripper_api.publication.publication_errors import (
    PublicationForbiddenError,
    PublicationRevisionConflictError,
    TripNotReadyToPublishError,
)
from tripper_api.publication.publication_repository import PublicationRepository
from tripper_api.trip.trip_errors import TripNotFoundError
from tripper_api.trip.trip_model import Trip


def _has_valid_destination_metadata(
    destinations: list[tuple[str, str]],
) -> bool:
    if not destinations:
        return False
    try:
        return all(
            bool(name.strip() and timezone.strip() and ZoneInfo(timezone))
            for name, timezone in destinations
        )
    except ZoneInfoNotFoundError:
        return False


class PublicationService:
    def __init__(
        self,
        session: AsyncSession,
        membership_repository: MembershipRepository,
        publication_repository: PublicationRepository,
    ) -> None:
        self._session = session
        self._membership_repository = membership_repository
        self._publication_repository = publication_repository

    async def get(self, trip_id: UUID, account_id: UUID) -> PublicationResponse:
        async with self._session.begin():
            trip = await self._creator_trip(trip_id, account_id)
            return self._response(trip)

    async def publish(
        self, trip_id: UUID, account_id: UUID, starting_revision: int
    ) -> PublicationResponse:
        async with self._session.begin():
            trip = await self._creator_trip(trip_id, account_id)
            self._check_revision(trip, starting_revision)
            destinations = await self._publication_repository.destination_metadata(
                trip.id
            )
            has_valid_destinations = await asyncio.to_thread(
                _has_valid_destination_metadata, destinations
            )
            if (
                not trip.name.strip()
                or not has_valid_destinations
                or not await self._publication_repository.has_populated_plan(trip.id)
            ):
                raise TripNotReadyToPublishError
            if trip.public_token is None:
                trip.public_token = token_urlsafe(32)
            trip.published_at = datetime.now(UTC)
            trip.publication_revision += 1
            await self._session.flush()
            return self._response(trip)

    async def unpublish(
        self, trip_id: UUID, account_id: UUID, starting_revision: int
    ) -> PublicationResponse:
        async with self._session.begin():
            trip = await self._creator_trip(trip_id, account_id)
            self._check_revision(trip, starting_revision)
            trip.published_at = None
            trip.publication_revision += 1
            await self._session.flush()
            return self._response(trip)

    async def rotate(
        self, trip_id: UUID, account_id: UUID, starting_revision: int
    ) -> PublicationResponse:
        async with self._session.begin():
            trip = await self._creator_trip(trip_id, account_id)
            self._check_revision(trip, starting_revision)
            trip.public_token = token_urlsafe(32)
            trip.publication_revision += 1
            await self._session.flush()
            return self._response(trip)

    async def _creator_trip(self, trip_id: UUID, account_id: UUID) -> Trip:
        access = await self._membership_repository.lock_trip_and_get_membership(
            trip_id, account_id
        )
        if access is None:
            raise TripNotFoundError
        if access.role is not TripRole.CREATOR:
            raise PublicationForbiddenError
        return access.trip

    @staticmethod
    def _check_revision(trip: Trip, starting_revision: int) -> None:
        if trip.publication_revision != starting_revision:
            raise PublicationRevisionConflictError

    @staticmethod
    def _response(trip: Trip) -> PublicationResponse:
        return PublicationResponse(
            is_published=trip.published_at is not None,
            public_token=trip.public_token,
            revision=trip.publication_revision,
        )
