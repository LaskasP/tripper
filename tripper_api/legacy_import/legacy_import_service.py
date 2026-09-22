import argparse
import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import date, time, timedelta
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tripper_api.auth.auth_model import Account
from tripper_api.core.config import Settings
from tripper_api.trip.trip_model import (
    DailyPlan,
    Destination,
    LegacyImport,
    Photo,
    Stay,
    TimelineEntry,
    Trip,
    TripMembership,
    TripRole,
)

IMPORT_KEY = "los_angeles_2026"
EXPECTED_SOURCE_SHA256 = (
    "a4959b50f8de841fa4417d119b2951a06b1930292f2bc8e5ccd905f750bf8955"
)
IMPORT_NAMESPACE = UUID("695a7d77-e70b-55a2-9f6d-b12a95ad1e8e")


class LegacyImportError(Exception):
    pass


class LegacySourceChangedError(LegacyImportError):
    pass


class LegacyTargetConflictError(LegacyImportError):
    pass


class _Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class _TripSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    short_name: str = Field(max_length=80)
    description: str
    timezone: str
    location: _Location
    start_date: date
    end_date: date

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA timezone") from error
        return value


class _TimelineSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time: time
    title: str = Field(min_length=1, max_length=200)
    description: str
    location: _Location | None = None
    location_name: str | None = None


class _StaySource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    address: str
    location: _Location | None = None
    check_in: time | None = None
    check_out: time | None = None
    public_listing_url: str | None = None
    booking_platform: str | None = None

    @field_validator("public_listing_url")
    @classmethod
    def https_listing(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("https://"):
            raise ValueError("public listing URL must use HTTPS")
        return value


class _PhotoSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    caption: str

    @field_validator("url")
    @classmethod
    def https_photo(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("photo URL must use HTTPS")
        return value


class _DaySource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    day_number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    summary: str
    background_image: str
    stay: _StaySource
    timeline: list[_TimelineSource]
    photos: list[_PhotoSource]

    @field_validator("background_image")
    @classmethod
    def https_background(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("background image URL must use HTTPS")
        return value


@dataclass(frozen=True)
class LegacyImportResult:
    status: Literal["validated", "imported", "already_imported"]
    trip_id: UUID
    source_sha256: str
    daily_plan_count: int
    timeline_entry_count: int
    stay_count: int
    photo_count: int


@dataclass(frozen=True)
class _ValidatedSource:
    trip: _TripSource
    days: tuple[_DaySource, ...]
    source_sha256: str


def _stable_id(path: str) -> UUID:
    return uuid5(IMPORT_NAMESPACE, path)


def _read_source(source_directory: Path) -> _ValidatedSource:
    try:
        trip_document = json.loads(
            (source_directory / "trip.json").read_text(encoding="utf-8")
        )
        days_document = json.loads(
            (source_directory / "days.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError, ValidationError, TypeError) as error:
        raise LegacyImportError(f"Invalid Los Angeles guide source: {error}") from error

    canonical = json.dumps(
        {"trip": trip_document, "days": days_document},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    source_sha256 = hashlib.sha256(canonical).hexdigest()
    try:
        if (
            not isinstance(trip_document, dict)
            or not isinstance(days_document, list)
            or not all(isinstance(day, dict) for day in days_document)
        ):
            raise TypeError("trip.json must be an object and days.json must be a list")
        trip = _TripSource.model_validate(trip_document)
        days = tuple(_DaySource.model_validate(day) for day in days_document)
    except (ValidationError, TypeError) as error:
        raise LegacyImportError(f"Invalid Los Angeles guide source: {error}") from error
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        raise LegacySourceChangedError(
            "The checked-in Los Angeles source differs from the reviewed source"
        )
    expected_dates = [
        trip.start_date + timedelta(days=offset)
        for offset in range((trip.end_date - trip.start_date).days + 1)
    ]
    if [day.date for day in days] != expected_dates:
        raise LegacyImportError("Daily plans must cover the Trip date range in order")
    if [day.day_number for day in days] != list(range(1, len(days) + 1)):
        raise LegacyImportError("Daily plan numbers must be consecutive")
    counts = (
        len(days),
        sum(len(day.timeline) for day in days),
        len([day for day in days if day.stay is not None]),
        sum(len(day.photos) for day in days),
    )
    if counts != (14, 98, 14, 42):
        raise LegacyImportError(
            "Los Angeles source must contain 14 Daily plans, 98 Timeline entries, "
            "14 Stays, and 42 photos"
        )
    return _ValidatedSource(trip=trip, days=days, source_sha256=source_sha256)


def _result(
    source: _ValidatedSource,
    status: Literal["validated", "imported", "already_imported"],
) -> LegacyImportResult:
    return LegacyImportResult(
        status=status,
        trip_id=_stable_id("trip"),
        source_sha256=source.source_sha256,
        daily_plan_count=len(source.days),
        timeline_entry_count=sum(len(day.timeline) for day in source.days),
        stay_count=len(source.days),
        photo_count=sum(len(day.photos) for day in source.days),
    )


async def _target_matches(
    session: AsyncSession, source: _ValidatedSource, creator_id: UUID
) -> bool:
    trip_id = _stable_id("trip")
    trip = await session.get(Trip, trip_id)
    destination_id = _stable_id("destination:0")
    destination = await session.get(Destination, destination_id)
    membership = await session.get(TripMembership, _stable_id("membership:creator"))
    if (
        trip is None
        or destination is None
        or membership is None
        or (
            trip.name,
            trip.short_name,
            trip.description,
            trip.start_date,
            trip.end_date,
        )
        != (
            source.trip.name,
            source.trip.short_name,
            source.trip.description,
            source.trip.start_date,
            source.trip.end_date,
        )
        or (
            destination.trip_id,
            destination.name,
            destination.timezone,
            destination.latitude,
            destination.longitude,
            destination.position,
        )
        != (
            trip_id,
            source.trip.destination,
            source.trip.timezone,
            source.trip.location.lat,
            source.trip.location.lng,
            0,
        )
        or (membership.trip_id, membership.account_id, membership.role)
        != (trip_id, creator_id, TripRole.CREATOR)
    ):
        return False
    expected = (
        len(source.days),
        sum(len(day.timeline) for day in source.days),
        len(source.days),
        sum(len(day.photos) for day in source.days),
    )
    actual = []
    for model, condition in (
        (DailyPlan, DailyPlan.trip_id == trip_id),
        (
            TimelineEntry,
            TimelineEntry.daily_plan_id.in_(
                select(DailyPlan.id).where(DailyPlan.trip_id == trip_id)
            ),
        ),
        (
            Stay,
            Stay.daily_plan_id.in_(
                select(DailyPlan.id).where(DailyPlan.trip_id == trip_id)
            ),
        ),
        (
            Photo,
            Photo.daily_plan_id.in_(
                select(DailyPlan.id).where(DailyPlan.trip_id == trip_id)
            ),
        ),
    ):
        actual.append(
            await session.scalar(
                select(func.count()).select_from(model).where(condition)
            )
        )
    if tuple(actual) != expected:
        return False
    for day_index, day in enumerate(source.days):
        plan_id = _stable_id(f"daily_plan:{day_index}")
        plan = await session.get(DailyPlan, plan_id)
        stay = await session.get(Stay, _stable_id(f"stay:{day_index}"))
        if (
            plan is None
            or stay is None
            or (
                plan.trip_id,
                plan.destination_id,
                plan.date,
                plan.title,
                plan.summary,
                plan.background_image,
            )
            != (
                trip_id,
                destination_id,
                day.date,
                day.title,
                day.summary,
                day.background_image,
            )
            or (
                stay.daily_plan_id,
                stay.name,
                stay.address,
                stay.latitude,
                stay.longitude,
                stay.check_in,
                stay.check_out,
                stay.public_listing_url,
                stay.booking_platform,
            )
            != (
                plan_id,
                day.stay.name,
                day.stay.address,
                day.stay.location.lat if day.stay.location is not None else None,
                day.stay.location.lng if day.stay.location is not None else None,
                day.stay.check_in,
                day.stay.check_out,
                day.stay.public_listing_url,
                day.stay.booking_platform,
            )
        ):
            return False
        for position, entry in enumerate(day.timeline):
            stored_entry = await session.get(
                TimelineEntry, _stable_id(f"timeline:{day_index}:{position}")
            )
            if stored_entry is None or (
                stored_entry.daily_plan_id,
                stored_entry.destination_id,
                stored_entry.local_time,
                stored_entry.title,
                stored_entry.description,
                stored_entry.location_name,
                stored_entry.latitude,
                stored_entry.longitude,
                stored_entry.position,
            ) != (
                plan_id,
                destination_id,
                entry.time,
                entry.title,
                entry.description,
                entry.location_name,
                entry.location.lat if entry.location is not None else None,
                entry.location.lng if entry.location is not None else None,
                position,
            ):
                return False
        for position, photo in enumerate(day.photos):
            stored_photo = await session.get(
                Photo, _stable_id(f"photo:{day_index}:{position}")
            )
            if stored_photo is None or (
                stored_photo.daily_plan_id,
                stored_photo.url,
                stored_photo.caption,
                stored_photo.position,
            ) != (plan_id, photo.url, photo.caption, position):
                return False
    return True


async def _add_import_rows(
    session: AsyncSession, source: _ValidatedSource, creator_id: UUID
) -> None:
    trip_id = _stable_id("trip")
    destination_id = _stable_id("destination:0")
    session.add(
        Trip(
            id=trip_id,
            name=source.trip.name,
            short_name=source.trip.short_name,
            description=source.trip.description,
            start_date=source.trip.start_date,
            end_date=source.trip.end_date,
        )
    )
    await session.flush()
    session.add(
        Destination(
            id=destination_id,
            trip_id=trip_id,
            name=source.trip.destination,
            timezone=source.trip.timezone,
            latitude=source.trip.location.lat,
            longitude=source.trip.location.lng,
            position=0,
        )
    )
    session.add(
        TripMembership(
            id=_stable_id("membership:creator"),
            trip_id=trip_id,
            account_id=creator_id,
            role=TripRole.CREATOR,
        )
    )
    await session.flush()
    for day_index, day in enumerate(source.days):
        plan_id = _stable_id(f"daily_plan:{day_index}")
        session.add(
            DailyPlan(
                id=plan_id,
                trip_id=trip_id,
                destination_id=destination_id,
                date=day.date,
                title=day.title,
                summary=day.summary,
                background_image=day.background_image,
            )
        )
        await session.flush()
        stay = day.stay
        session.add(
            Stay(
                id=_stable_id(f"stay:{day_index}"),
                daily_plan_id=plan_id,
                name=stay.name,
                address=stay.address,
                latitude=stay.location.lat if stay.location is not None else None,
                longitude=stay.location.lng if stay.location is not None else None,
                check_in=stay.check_in,
                check_out=stay.check_out,
                public_listing_url=stay.public_listing_url,
                booking_platform=stay.booking_platform,
            )
        )
        session.add_all(
            TimelineEntry(
                id=_stable_id(f"timeline:{day_index}:{position}"),
                daily_plan_id=plan_id,
                destination_id=destination_id,
                local_time=entry.time,
                title=entry.title,
                description=entry.description,
                location_name=entry.location_name,
                latitude=entry.location.lat if entry.location is not None else None,
                longitude=entry.location.lng if entry.location is not None else None,
                position=position,
            )
            for position, entry in enumerate(day.timeline)
        )
        session.add_all(
            Photo(
                id=_stable_id(f"photo:{day_index}:{position}"),
                daily_plan_id=plan_id,
                url=photo.url,
                caption=photo.caption,
                position=position,
            )
            for position, photo in enumerate(day.photos)
        )
    session.add(
        LegacyImport(
            import_key=IMPORT_KEY,
            source_sha256=source.source_sha256,
            trip_id=trip_id,
        )
    )


async def import_los_angeles_guide(
    *,
    settings: Settings,
    creator_id: UUID,
    source_directory: Path,
    dry_run: bool = False,
) -> LegacyImportResult:
    source = await asyncio.to_thread(_read_source, source_directory)
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:import_key))"),
                {"import_key": IMPORT_KEY},
            )
            if await session.get(Account, creator_id) is None:
                raise LegacyImportError("The chosen Creator Account does not exist")
            history = await session.get(LegacyImport, IMPORT_KEY)
            target = await session.get(Trip, _stable_id("trip"))
            if history is not None:
                if history.source_sha256 != source.source_sha256:
                    raise LegacyTargetConflictError(
                        "Import history records a different source"
                    )
                if history.trip_id != _stable_id("trip") or not await _target_matches(
                    session, source, creator_id
                ):
                    raise LegacyTargetConflictError(
                        "The imported target is partial or conflicts with history"
                    )
                return _result(source, "already_imported")
            if target is not None:
                raise LegacyTargetConflictError(
                    "A partial Los Angeles import target already exists"
                )
            if dry_run:
                return _result(source, "validated")
            await _add_import_rows(session, source, creator_id)
        return _result(source, "imported")
    finally:
        await engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import the Los Angeles guide")
    parser.add_argument("--creator-id", required=True, type=UUID)
    parser.add_argument(
        "--source-directory",
        type=Path,
        default=Path("legacy_data/los_angeles"),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


async def _main() -> int:
    arguments = _parser().parse_args()
    try:
        result = await import_los_angeles_guide(
            settings=Settings(),
            creator_id=arguments.creator_id,
            source_directory=arguments.source_directory,
            dry_run=arguments.dry_run,
        )
    except LegacyImportError as error:
        print(f"Import refused: {error}")
        return 1
    print(json.dumps({key: str(value) for key, value in result.__dict__.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
