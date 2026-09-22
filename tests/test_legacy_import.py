import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.test_trips_api import ALEX_ID, app_client
from tripper_api.core.config import Settings
from tripper_api.legacy_import import (
    LegacyImportError,
    LegacySourceChangedError,
    LegacyTargetConflictError,
    import_los_angeles_guide,
)

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]

SOURCE_DIRECTORY = Path("legacy_data/los_angeles")


async def add_creator(settings: Settings) -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO accounts (id, issuer, subject, email, display_name) "
                "VALUES (:id, 'test', :subject, 'alex@example.com', 'Alex Creator')"
            ),
            {"id": UUID(ALEX_ID), "subject": ALEX_ID},
        )
    await engine.dispose()


async def test_imported_guide_is_complete_and_readable_by_its_creator(
    database_settings: Settings,
) -> None:
    await add_creator(database_settings)

    result = await import_los_angeles_guide(
        settings=database_settings,
        creator_id=UUID(ALEX_ID),
        source_directory=SOURCE_DIRECTORY,
    )

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        response = await client.get(f"/api/trips/{result.trip_id}")

    assert result.status == "imported"
    assert result.daily_plan_count == 14
    assert result.timeline_entry_count == 98
    assert result.stay_count == 14
    assert result.photo_count == 42
    assert response.status_code == 200
    guide = response.json()
    assert guide["name"] == "Los Angeles 2026"
    assert guide["location"] == {"lat": 34.0522, "lng": -118.2437}
    assert len(guide["daily_plans"]) == 14
    assert sum(len(day["timeline"]) for day in guide["daily_plans"]) == 98
    assert sum(len(day["photos"]) for day in guide["daily_plans"]) == 42
    assert all(day["stay"] is not None for day in guide["daily_plans"])
    first_day = guide["daily_plans"][0]
    assert first_day["date"] == "2026-11-13"
    assert first_day["day_number"] == 1
    assert first_day["title"] == "Arrival at Downtown LA"
    assert first_day["timeline"][0]["title"] == "Arrive at LAX"
    assert first_day["photos"][0]["caption"] == "Downtown LA skyline"
    source_days = json.loads(
        (SOURCE_DIRECTORY / "days.json").read_text(encoding="utf-8")
    )
    for actual, expected in zip(guide["daily_plans"], source_days, strict=True):
        assert actual["date"] == expected["date"]
        assert actual["day_number"] == expected["day_number"]
        assert actual["title"] == expected["title"]
        assert actual["summary"] == expected["summary"]
        assert actual["background_image"] == expected["background_image"]
        assert actual["photos"] == expected["photos"]
        assert [
            {
                **entry,
                "time": entry["time"][:5],
            }
            for entry in actual["timeline"]
        ] == [
            {
                "time": entry["time"],
                "title": entry["title"],
                "description": entry["description"],
                "location": entry.get("location"),
                "location_name": entry.get("location_name"),
            }
            for entry in expected["timeline"]
        ]
        expected_stay = expected["stay"]
        assert actual["stay"] == {
            "name": expected_stay["name"],
            "address": expected_stay["address"],
            "location": expected_stay.get("location"),
            "check_in": (
                f"{expected_stay['check_in']}:00"
                if expected_stay.get("check_in")
                else None
            ),
            "check_out": (
                f"{expected_stay['check_out']}:00"
                if expected_stay.get("check_out")
                else None
            ),
            "public_listing_url": expected_stay.get("public_listing_url"),
            "booking_platform": expected_stay.get("booking_platform"),
        }


async def test_dry_run_validates_without_creating_a_trip(
    database_settings: Settings,
) -> None:
    await add_creator(database_settings)

    result = await import_los_angeles_guide(
        settings=database_settings,
        creator_id=UUID(ALEX_ID),
        source_directory=SOURCE_DIRECTORY,
        dry_run=True,
    )

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        trips = await client.get("/api/me/trips")
    assert result.status == "validated"
    assert trips.json() == []


async def test_identical_rerun_is_a_no_op(database_settings: Settings) -> None:
    await add_creator(database_settings)
    first = await import_los_angeles_guide(
        settings=database_settings,
        creator_id=UUID(ALEX_ID),
        source_directory=SOURCE_DIRECTORY,
    )
    second = await import_los_angeles_guide(
        settings=database_settings,
        creator_id=UUID(ALEX_ID),
        source_directory=SOURCE_DIRECTORY,
    )

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        trips = await client.get("/api/me/trips")
        guide = await client.get(f"/api/trips/{first.trip_id}")
    assert second.status == "already_imported"
    assert len(trips.json()) == 1
    assert len(guide.json()["daily_plans"]) == 14


async def test_changed_or_invalid_source_is_rejected_without_writes(
    database_settings: Settings,
) -> None:
    await add_creator(database_settings)
    with TemporaryDirectory(dir=".") as temporary_directory:
        temporary_path = Path(temporary_directory)
        changed_source = temporary_path / "changed"
        changed_source.mkdir()
        trip = json.loads((SOURCE_DIRECTORY / "trip.json").read_text(encoding="utf-8"))
        trip["name"] = "Changed"
        (changed_source / "trip.json").write_text(json.dumps(trip), encoding="utf-8")
        (changed_source / "days.json").write_text(
            (SOURCE_DIRECTORY / "days.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        invalid_source = temporary_path / "invalid"
        invalid_source.mkdir()
        (invalid_source / "trip.json").write_text("{}", encoding="utf-8")
        (invalid_source / "days.json").write_text("[]", encoding="utf-8")

        with pytest.raises(LegacySourceChangedError):
            await import_los_angeles_guide(
                settings=database_settings,
                creator_id=UUID(ALEX_ID),
                source_directory=changed_source,
            )
        with pytest.raises(LegacyImportError):
            await import_los_angeles_guide(
                settings=database_settings,
                creator_id=UUID(ALEX_ID),
                source_directory=invalid_source,
            )

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        trips = await client.get("/api/me/trips")
    assert trips.json() == []


async def test_partial_target_and_conflicting_history_are_never_repaired(
    database_settings: Settings,
) -> None:
    await add_creator(database_settings)
    imported = await import_los_angeles_guide(
        settings=database_settings,
        creator_id=UUID(ALEX_ID),
        source_directory=SOURCE_DIRECTORY,
    )
    engine = create_async_engine(database_settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "DELETE FROM photos WHERE id = "
                "(SELECT id FROM photos ORDER BY id LIMIT 1)"
            )
        )
    await engine.dispose()

    with pytest.raises(LegacyTargetConflictError):
        await import_los_angeles_guide(
            settings=database_settings,
            creator_id=UUID(ALEX_ID),
            source_directory=SOURCE_DIRECTORY,
        )

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        guide = await client.get(f"/api/trips/{imported.trip_id}")
    assert sum(len(day["photos"]) for day in guide.json()["daily_plans"]) == 41

    engine = create_async_engine(database_settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE legacy_imports SET source_sha256 = :source_sha256 "
                "WHERE import_key = 'los_angeles_2026'"
            ),
            {"source_sha256": "0" * 64},
        )
    await engine.dispose()
    with pytest.raises(LegacyTargetConflictError):
        await import_los_angeles_guide(
            settings=database_settings,
            creator_id=UUID(ALEX_ID),
            source_directory=SOURCE_DIRECTORY,
        )


async def test_rerun_refuses_changed_canonical_values(
    database_settings: Settings,
) -> None:
    await add_creator(database_settings)
    imported = await import_los_angeles_guide(
        settings=database_settings,
        creator_id=UUID(ALEX_ID),
        source_directory=SOURCE_DIRECTORY,
    )
    engine = create_async_engine(database_settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE photos SET caption = 'Changed after import' "
                "WHERE id = (SELECT id FROM photos ORDER BY id LIMIT 1)"
            )
        )
    await engine.dispose()

    with pytest.raises(LegacyTargetConflictError):
        await import_los_angeles_guide(
            settings=database_settings,
            creator_id=UUID(ALEX_ID),
            source_directory=SOURCE_DIRECTORY,
        )
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        guide = await client.get(f"/api/trips/{imported.trip_id}")
    assert any(
        photo["caption"] == "Changed after import"
        for day in guide.json()["daily_plans"]
        for photo in day["photos"]
    )
