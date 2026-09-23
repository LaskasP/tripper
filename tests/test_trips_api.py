import asyncio
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tripper_api.app import create_app
from tripper_api.core.config import Settings
from tripper_api.core.security import AuthenticatedUser, require_current_user

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]


TRIP = {
    "name": "Greek Islands 2027",
    "destination": "Cyclades",
    "short_name": "Greek Islands",
    "description": "A week through the Cyclades",
    "timezone": "Europe/Athens",
    "location": {"lat": 37.4467, "lng": 25.3289},
    "start_date": "2027-06-10",
    "end_date": "2027-06-17",
}

ALEX_ID = "a7bff584-bfcd-4d4a-86f8-ece48870e67a"
JAMIE_ID = "83c801db-7558-4f93-bb03-6025479920fc"
MORGAN_ID = "2a385a2e-8800-4e45-91ea-cbec7e264876"


async def app_client(
    settings: Settings,
    user: dict[str, str] | None = None,
) -> AsyncIterator[tuple[AsyncClient, FastAPI]]:
    if user is not None:
        engine = create_async_engine(settings.database_url)
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO accounts (id, issuer, subject, email, display_name) "
                    "VALUES (:id, 'test', :subject, 'test@example.com', 'Test User') "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": UUID(user["id"]), "subject": user["id"]},
            )
        await engine.dispose()
    app = create_app(settings)
    if user is not None:
        app.dependency_overrides[require_current_user] = lambda: AuthenticatedUser(
            id=UUID(user["id"]),
            session_id=UUID("00000000-0000-0000-0000-000000000001"),
            email="test@example.com",
            display_name="Test User",
        )

    async with (
        LifespanManager(app),
        AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client,
    ):
        yield client, app


async def add_participant(
    settings: Settings,
    *,
    trip_id: str,
    account_id: str,
    display_name: str,
    role: str,
) -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO accounts (id, issuer, subject, email, display_name) "
                "VALUES (:account_id, 'test', :subject, :email, :display_name)"
            ),
            {
                "account_id": UUID(account_id),
                "subject": account_id,
                "email": f"{account_id}@example.com",
                "display_name": display_name,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO trip_memberships (id, trip_id, account_id, role) "
                "VALUES (:id, :trip_id, :account_id, :role)"
            ),
            {
                "id": uuid4(),
                "trip_id": UUID(trip_id),
                "account_id": UUID(account_id),
                "role": role,
            },
        )
    await engine.dispose()


async def remove_participant(
    settings: Settings, *, trip_id: str, account_id: str
) -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "DELETE FROM trip_memberships "
                "WHERE trip_id = :trip_id AND account_id = :account_id"
            ),
            {"trip_id": UUID(trip_id), "account_id": UUID(account_id)},
        )
    await engine.dispose()


async def add_daily_plan(
    settings: Settings,
    *,
    trip_id: str,
    destination_id: str,
    plan_date: str,
) -> UUID:
    plan_id = uuid4()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO daily_plans "
                "(id, trip_id, destination_id, date, title, summary, background_image) "
                "VALUES (:id, :trip_id, :destination_id, :date, 'Planned day', '', '')"
            ),
            {
                "id": plan_id,
                "trip_id": UUID(trip_id),
                "destination_id": UUID(destination_id),
                "date": plan_date,
            },
        )
    await engine.dispose()
    return plan_id


async def add_timeline_entry(
    settings: Settings,
    *,
    daily_plan_id: UUID,
    destination_id: str,
) -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO timeline_entries "
                "(id, daily_plan_id, destination_id, local_time, title, description, "
                "position) VALUES (:id, :daily_plan_id, :destination_id, "
                "'09:00', 'Athens stop', '', 0)"
            ),
            {
                "id": uuid4(),
                "daily_plan_id": daily_plan_id,
                "destination_id": UUID(destination_id),
            },
        )
    await engine.dispose()


async def test_editor_creates_edits_and_clears_one_daily_plan(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await client.post("/api/trips", json=TRIP)).json()["id"]
        before = (await client.get(f"/api/trips/{trip_id}")).json()
        date = "2027-06-11"
        created = await client.put(
            f"/api/trips/{trip_id}/daily-plans/{date}",
            json={
                "starting_revision": before["content_revision"],
                "destination_id": before["destinations"][0]["id"],
                "title": "Island arrival",
                "summary": "Ferry and dinner",
                "background_image": "https://example.com/island.jpg",
            },
        )
        assert created.status_code == 200
        saved = created.json()
        plan = saved["daily_plans"][0]
        assert (plan["date"], plan["title"], plan["summary"]) == (
            date,
            "Island arrival",
            "Ferry and dinner",
        )
        assert saved["calendar"][1]["is_planned"] is True
        assert saved["calendar"][0]["is_planned"] is False

        edited = await client.put(
            f"/api/trips/{trip_id}/daily-plans/{date}",
            json={
                "id": plan["id"],
                "starting_revision": plan["revision"],
                "destination_id": plan["destination_id"],
                "title": "Island day",
                "summary": "",
                "background_image": "",
            },
        )
        assert edited.status_code == 200
        assert edited.json()["daily_plans"][0]["id"] == plan["id"]
        assert edited.json()["daily_plans"][0]["revision"] == plan["revision"] + 1

        cleared = await client.request(
            "DELETE",
            f"/api/trips/{trip_id}/daily-plans/{date}",
            json={"starting_revision": plan["revision"] + 1},
        )
        assert cleared.status_code == 200
        assert cleared.json()["daily_plans"] == []
        assert cleared.json()["calendar"][1]["is_planned"] is False


async def test_move_daily_plan_preserves_its_content_and_rejects_occupied_target(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await client.post("/api/trips", json=TRIP)).json()["id"]
        detail = (await client.get(f"/api/trips/{trip_id}")).json()
        destination_id = detail["destinations"][0]["id"]
        plan_id = await add_daily_plan(
            database_settings,
            trip_id=trip_id,
            destination_id=destination_id,
            plan_date="2027-06-10",
        )
        await add_timeline_entry(
            database_settings, daily_plan_id=plan_id, destination_id=destination_id
        )
        target_id = await add_daily_plan(
            database_settings,
            trip_id=trip_id,
            destination_id=destination_id,
            plan_date="2027-06-12",
        )
        source = (await client.get(f"/api/trips/{trip_id}")).json()["daily_plans"][0]
        move_path = f"/api/trips/{trip_id}/daily-plans/{plan_id}/move"
        occupied = await client.post(
            move_path,
            json={"starting_revision": source["revision"], "target_date": "2027-06-12"},
        )
        outside = await client.post(
            move_path,
            json={"starting_revision": source["revision"], "target_date": "2027-06-18"},
        )
        assert occupied.status_code == 409
        assert outside.status_code == 422
        assert [
            p["date"]
            for p in (await client.get(f"/api/trips/{trip_id}")).json()["daily_plans"]
        ] == ["2027-06-10", "2027-06-12"]

        moved = await client.post(
            move_path,
            json={"starting_revision": source["revision"], "target_date": "2027-06-11"},
        )
        assert moved.status_code == 200
        plans = moved.json()["daily_plans"]
        assert plans[0]["id"] == str(plan_id)
        assert plans[0]["date"] == "2027-06-11"
        assert plans[0]["timeline"][0]["title"] == "Athens stop"
        assert plans[1]["id"] == str(target_id)
        assert (
            await client.post(
                move_path,
                json={
                    "starting_revision": source["revision"],
                    "target_date": "2027-06-13",
                },
            )
        ).status_code == 409


async def test_daily_plan_writes_reject_stale_creation_invalid_input_and_travellers(
    database_settings: Settings,
) -> None:
    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await creator.post("/api/trips", json=TRIP)).json()["id"]
        before = (await creator.get(f"/api/trips/{trip_id}")).json()
        path = f"/api/trips/{trip_id}/daily-plans/2027-06-10"
        payload = {
            "starting_revision": before["content_revision"],
            "destination_id": before["destinations"][0]["id"],
            "title": "Arrival",
            "summary": "",
            "background_image": "",
        }
        invalid_image = await creator.put(
            path, json={**payload, "background_image": "http://example.com/image.jpg"}
        )
        invalid_destination = await creator.put(
            path, json={**payload, "destination_id": str(uuid4())}
        )
        assert invalid_image.status_code == 422
        assert invalid_destination.status_code == 422
        assert (await creator.get(f"/api/trips/{trip_id}")).json()["daily_plans"] == []

        saved = await creator.put(path, json=payload)
        assert saved.status_code == 200
        duplicate = await creator.put(path, json=payload)
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "daily_plan_revision_conflict"
        assert (
            duplicate.json()["error"]["latest_values"]["daily_plans"][0]["title"]
            == "Arrival"
        )
        stale = await creator.put(
            path,
            json={
                **payload,
                "id": saved.json()["daily_plans"][0]["id"],
                "starting_revision": 100,
            },
        )
        assert stale.status_code == 409
        assert (
            stale.json()["error"]["latest_values"]["daily_plans"][0]["title"]
            == "Arrival"
        )
        assert (await creator.get(f"/api/trips/{trip_id}")).json()["daily_plans"][0][
            "title"
        ] == "Arrival"

    await add_participant(
        database_settings,
        trip_id=trip_id,
        account_id=JAMIE_ID,
        display_name="Jamie",
        role="traveller",
    )
    async for traveller, _ in app_client(database_settings, {"id": JAMIE_ID}):
        forbidden = await traveller.put(
            path,
            json={
                **payload,
                "id": saved.json()["daily_plans"][0]["id"],
                "title": "Forbidden",
            },
        )
        assert forbidden.status_code == 403
        assert (await traveller.get(f"/api/trips/{trip_id}")).json()["daily_plans"][0][
            "title"
        ] == "Arrival"


async def test_editor_creates_edits_and_clears_an_independent_stay(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await client.post("/api/trips", json=TRIP)).json()["id"]
        detail = (await client.get(f"/api/trips/{trip_id}")).json()
        current = detail
        for plan_date in ("2027-06-10", "2027-06-11"):
            response = await client.put(
                f"/api/trips/{trip_id}/daily-plans/{plan_date}",
                json={
                    "starting_revision": current["content_revision"],
                    "destination_id": detail["destinations"][0]["id"],
                    "title": "Island day",
                    "summary": "",
                    "background_image": "",
                },
            )
            current = response.json()
        first_plan, second_plan = current["daily_plans"]
        first_path = f"/api/trips/{trip_id}/daily-plans/{first_plan['id']}/stay"
        second_path = f"/api/trips/{trip_id}/daily-plans/{second_plan['id']}/stay"

        first_created = await client.put(
            first_path,
            json={
                "starting_revision": first_plan["revision"],
                "name": "  Aegean House  ",
                "address": "  Port Road 1  ",
                "location": {"lat": 37.45, "lng": 25.33},
                "check_in": "15:00",
                "check_out": "11:00",
                "booking_platform": "airbnb",
                "public_listing_url": "https://example.com/aegean-house",
            },
        )
        first_stay = first_created.json()["daily_plans"][0]["stay"]
        second_created = await client.put(
            second_path,
            json={
                "starting_revision": second_plan["revision"],
                "name": "Harbour Hotel",
            },
        )
        edited = await client.put(
            first_path,
            json={
                "id": first_stay["id"],
                "starting_revision": first_stay["revision"],
                "name": "Aegean Suites",
                "address": "",
                "booking_platform": "booking.com",
                "public_listing_url": "https://example.com/aegean-suites",
            },
        )
        edited_stay = edited.json()["daily_plans"][0]["stay"]
        cleared = await client.request(
            "DELETE",
            first_path,
            json={"starting_revision": edited_stay["revision"]},
        )

    assert first_created.status_code == 200
    assert first_stay["name"] == "Aegean House"
    assert first_stay["address"] == "Port Road 1"
    assert first_stay["location"] == {"lat": 37.45, "lng": 25.33}
    assert first_stay["check_in"] == "15:00:00"
    assert first_stay["check_out"] == "11:00:00"
    assert first_stay["revision"] == 1
    assert second_created.status_code == 200
    assert edited_stay["id"] == first_stay["id"]
    assert edited_stay["revision"] == 2
    assert edited_stay["name"] == "Aegean Suites"
    assert edited_stay["location"] is None
    assert cleared.status_code == 200
    first_after_clear, second_after_clear = cleared.json()["daily_plans"]
    assert first_after_clear["stay"] is None
    assert second_after_clear["stay"]["name"] == "Harbour Hotel"


async def test_stay_writes_reject_invalid_private_stale_and_unauthorized_data(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        trip_id = (await client.post("/api/trips", json=TRIP)).json()["id"]
        detail = (await client.get(f"/api/trips/{trip_id}")).json()
        with_plan = await client.put(
            f"/api/trips/{trip_id}/daily-plans/2027-06-10",
            json={
                "starting_revision": detail["content_revision"],
                "destination_id": detail["destinations"][0]["id"],
                "title": "Arrival",
                "summary": "",
                "background_image": "",
            },
        )
        plan = with_plan.json()["daily_plans"][0]
        path = f"/api/trips/{trip_id}/daily-plans/{plan['id']}/stay"
        base = {
            "starting_revision": plan["revision"],
            "name": "Aegean House",
        }
        invalid_requests = [
            {**base, "name": "   "},
            {**base, "location": {"lat": 91, "lng": 25}},
            {**base, "check_in": "15:00+02:00"},
            {**base, "booking_platform": "direct"},
            {**base, "public_listing_url": "http://example.com/private"},
            {**base, "confirmation_number": "SECRET"},
        ]
        rejected = [
            await client.put(path, json=request) for request in invalid_requests
        ]
        created = await client.put(path, json=base)
        stay = created.json()["daily_plans"][0]["stay"]
        stale = await client.put(
            path,
            json={
                "id": stay["id"],
                "starting_revision": stay["revision"] + 1,
                "name": "Stale edit",
            },
        )
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=JAMIE_ID,
            display_name="Jamie Traveller",
            role="traveller",
        )
        user["id"] = JAMIE_ID
        forbidden = await client.request(
            "DELETE", path, json={"starting_revision": stay["revision"]}
        )
        unchanged = await client.get(f"/api/trips/{trip_id}")

    assert all(response.status_code == 422 for response in rejected)
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stay_revision_conflict"
    assert forbidden.status_code == 403
    projected = unchanged.json()["daily_plans"][0]["stay"]
    assert projected["name"] == "Aegean House"
    assert set(projected) == {
        "id",
        "revision",
        "name",
        "address",
        "location",
        "check_in",
        "check_out",
        "public_listing_url",
        "booking_platform",
    }


async def test_editor_creates_independent_timeline_entries_in_chronological_order(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await client.post("/api/trips", json=TRIP)).json()["id"]
        before = (await client.get(f"/api/trips/{trip_id}")).json()
        plan_response = await client.put(
            f"/api/trips/{trip_id}/daily-plans/2027-06-10",
            json={
                "starting_revision": before["content_revision"],
                "destination_id": before["destinations"][0]["id"],
                "title": "Arrival",
                "summary": "",
                "background_image": "",
            },
        )
        plan = plan_response.json()["daily_plans"][0]
        path = f"/api/trips/{trip_id}/daily-plans/{plan['id']}/timeline"

        late = await client.post(
            path,
            json={
                "starting_revision": plan["timeline_revision"],
                "time": "11:30",
                "title": "Museum",
                "description": "Independent stop",
                "location_name": "Acropolis Museum",
            },
        )
        equal = await client.post(
            path,
            json={
                "starting_revision": late.json()["daily_plans"][0]["timeline_revision"],
                "destination_id": before["destinations"][0]["id"],
                "time": "11:30",
                "title": "Coffee",
            },
        )
        early = await client.post(
            path,
            json={
                "starting_revision": equal.json()["daily_plans"][0][
                    "timeline_revision"
                ],
                "time": "09:00",
                "title": "Breakfast",
            },
        )

    assert late.status_code == 201
    assert equal.status_code == 201
    assert early.status_code == 201
    saved_plan = early.json()["daily_plans"][0]
    assert [entry["title"] for entry in saved_plan["timeline"]] == [
        "Breakfast",
        "Museum",
        "Coffee",
    ]
    assert len({entry["id"] for entry in saved_plan["timeline"]}) == 3
    assert all(entry["revision"] == 1 for entry in saved_plan["timeline"])
    assert all(entry["timezone"] == "Europe/Athens" for entry in saved_plan["timeline"])
    assert saved_plan["timeline"][1]["destination_id"] is None
    assert (
        saved_plan["timeline"][2]["destination_id"] == before["destinations"][0]["id"]
    )


async def test_editor_edits_and_deletes_one_timeline_entry_without_recreating_it(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await client.post("/api/trips", json=TRIP)).json()["id"]
        before = (await client.get(f"/api/trips/{trip_id}")).json()
        with_plan = await client.put(
            f"/api/trips/{trip_id}/daily-plans/2027-06-10",
            json={
                "starting_revision": before["content_revision"],
                "destination_id": before["destinations"][0]["id"],
                "title": "Arrival",
                "summary": "",
                "background_image": "",
            },
        )
        plan = with_plan.json()["daily_plans"][0]
        collection_path = f"/api/trips/{trip_id}/daily-plans/{plan['id']}/timeline"
        created = await client.post(
            collection_path,
            json={
                "starting_revision": plan["timeline_revision"],
                "time": "10:00",
                "title": "Old title",
            },
        )
        entry = created.json()["daily_plans"][0]["timeline"][0]
        entry_path = f"{collection_path}/{entry['id']}"

        edited = await client.put(
            entry_path,
            json={
                "starting_revision": entry["revision"],
                "time": "08:15",
                "title": "Breakfast",
                "description": "Meet downstairs",
                "location_name": "Hotel cafe",
                "location": {"lat": 37.98, "lng": 23.72},
            },
        )
        edited_plan = edited.json()["daily_plans"][0]
        saved_entry = edited_plan["timeline"][0]
        deleted = await client.request(
            "DELETE",
            entry_path,
            json={
                "starting_revision": saved_entry["revision"],
                "starting_collection_revision": edited_plan["timeline_revision"],
            },
        )

    assert edited.status_code == 200
    assert saved_entry["id"] == entry["id"]
    assert saved_entry["revision"] == entry["revision"] + 1
    assert saved_entry["title"] == "Breakfast"
    assert saved_entry["time"] == "08:15:00"
    assert saved_entry["location"] == {"lat": 37.98, "lng": 23.72}
    assert deleted.status_code == 200
    assert deleted.json()["daily_plans"][0]["timeline"] == []


async def test_timeline_reorder_is_atomic_and_rejects_a_stale_collection(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await client.post("/api/trips", json=TRIP)).json()["id"]
        detail = (await client.get(f"/api/trips/{trip_id}")).json()
        with_plan = await client.put(
            f"/api/trips/{trip_id}/daily-plans/2027-06-10",
            json={
                "starting_revision": detail["content_revision"],
                "destination_id": detail["destinations"][0]["id"],
                "title": "Arrival",
                "summary": "",
                "background_image": "",
            },
        )
        plan = with_plan.json()["daily_plans"][0]
        collection_path = f"/api/trips/{trip_id}/daily-plans/{plan['id']}/timeline"
        current = with_plan.json()
        for title in ("First", "Second", "Third"):
            plan = current["daily_plans"][0]
            response = await client.post(
                collection_path,
                json={
                    "starting_revision": plan["timeline_revision"],
                    "time": "10:00",
                    "title": title,
                },
            )
            current = response.json()
        plan = current["daily_plans"][0]
        original_ids = [entry["id"] for entry in plan["timeline"]]
        reordered = await client.post(
            f"{collection_path}/reorder",
            json={
                "starting_revision": plan["timeline_revision"],
                "entry_ids": list(reversed(original_ids)),
            },
        )
        stale = await client.post(
            f"{collection_path}/reorder",
            json={
                "starting_revision": plan["timeline_revision"],
                "entry_ids": original_ids,
            },
        )

    assert reordered.status_code == 200
    assert [
        entry["id"] for entry in reordered.json()["daily_plans"][0]["timeline"]
    ] == list(reversed(original_ids))
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "timeline_collection_revision_conflict"
    assert [
        entry["id"]
        for entry in stale.json()["error"]["latest_values"]["daily_plans"][0][
            "timeline"
        ]
    ] == list(reversed(original_ids))


async def test_timeline_move_preserves_identity_and_rejects_stale_collections(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await client.post("/api/trips", json=TRIP)).json()["id"]
        detail = (await client.get(f"/api/trips/{trip_id}")).json()
        current = detail
        for plan_date, title in (("2027-06-10", "Athens"), ("2027-06-11", "Island")):
            response = await client.put(
                f"/api/trips/{trip_id}/daily-plans/{plan_date}",
                json={
                    "starting_revision": current["content_revision"],
                    "destination_id": detail["destinations"][0]["id"],
                    "title": title,
                    "summary": "",
                    "background_image": "",
                },
            )
            current = response.json()
        source, target = current["daily_plans"]
        source_path = f"/api/trips/{trip_id}/daily-plans/{source['id']}/timeline"
        created = await client.post(
            source_path,
            json={
                "starting_revision": source["timeline_revision"],
                "time": "12:00",
                "title": "Lunch",
            },
        )
        source, target = created.json()["daily_plans"]
        entry = source["timeline"][0]
        move_path = f"{source_path}/{entry['id']}/move"
        stale_target_revision = target["timeline_revision"]
        target_path = f"/api/trips/{trip_id}/daily-plans/{target['id']}/timeline"
        target_changed = await client.post(
            target_path,
            json={
                "starting_revision": stale_target_revision,
                "time": "08:00",
                "title": "Coffee",
            },
        )
        source, target = target_changed.json()["daily_plans"]
        rejected = await client.post(
            move_path,
            json={
                "source_starting_revision": source["timeline_revision"],
                "target_plan_id": target["id"],
                "target_starting_revision": stale_target_revision,
            },
        )
        latest_source, latest_target = rejected.json()["error"]["latest_values"][
            "daily_plans"
        ]
        moved = await client.post(
            move_path,
            json={
                "source_starting_revision": latest_source["timeline_revision"],
                "target_plan_id": latest_target["id"],
                "target_starting_revision": latest_target["timeline_revision"],
            },
        )

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "timeline_collection_revision_conflict"
    assert [item["id"] for item in latest_source["timeline"]] == [entry["id"]]
    assert moved.status_code == 200
    moved_source, moved_target = moved.json()["daily_plans"]
    assert moved_source["timeline"] == []
    assert [item["title"] for item in moved_target["timeline"]] == ["Coffee", "Lunch"]
    assert moved_target["timeline"][1]["id"] == entry["id"]
    assert moved_target["timeline"][1]["revision"] == entry["revision"]


async def test_timeline_writes_validate_local_fields_and_editor_permission(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        trip_id = (await client.post("/api/trips", json=TRIP)).json()["id"]
        detail = (await client.get(f"/api/trips/{trip_id}")).json()
        saved = await client.put(
            f"/api/trips/{trip_id}/daily-plans/2027-06-10",
            json={
                "starting_revision": detail["content_revision"],
                "destination_id": detail["destinations"][0]["id"],
                "title": "Arrival",
                "summary": "",
                "background_image": "",
            },
        )
        plan = saved.json()["daily_plans"][0]
        path = f"/api/trips/{trip_id}/daily-plans/{plan['id']}/timeline"
        base = {
            "starting_revision": plan["timeline_revision"],
            "time": "10:00",
            "title": "Breakfast",
        }
        blank_title = await client.post(path, json={**base, "title": "   "})
        offset_time = await client.post(path, json={**base, "time": "10:00+02:00"})
        invalid_destination = await client.post(
            path, json={**base, "destination_id": str(uuid4())}
        )
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=JAMIE_ID,
            display_name="Jamie Traveller",
            role="traveller",
        )
        user["id"] = JAMIE_ID
        forbidden = await client.post(path, json=base)
        unchanged = await client.get(f"/api/trips/{trip_id}")

    assert blank_title.status_code == 422
    assert offset_time.status_code == 422
    assert invalid_destination.status_code == 422
    assert forbidden.status_code == 403
    assert unchanged.json()["daily_plans"][0]["timeline"] == []


async def test_editor_adds_reorders_and_removes_photos_with_stable_identities(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await client.post("/api/trips", json=TRIP)).json()["id"]
        detail = (await client.get(f"/api/trips/{trip_id}")).json()
        with_plan = await client.put(
            f"/api/trips/{trip_id}/daily-plans/2027-06-10",
            json={
                "starting_revision": detail["content_revision"],
                "destination_id": detail["destinations"][0]["id"],
                "title": "Arrival",
                "summary": "",
                "background_image": "",
            },
        )
        plan = with_plan.json()["daily_plans"][0]
        collection_path = f"/api/trips/{trip_id}/daily-plans/{plan['id']}/photos"
        first = await client.post(
            collection_path,
            json={
                "starting_revision": plan["photo_revision"],
                "url": "https://images.example/first.jpg",
                "caption": "First view",
            },
        )
        plan = first.json()["daily_plans"][0]
        second = await client.post(
            collection_path,
            json={
                "starting_revision": plan["photo_revision"],
                "url": "https://images.example/second.jpg",
                "caption": "Second view",
            },
        )
        plan = second.json()["daily_plans"][0]
        original = plan["photos"]
        reordered = await client.post(
            f"{collection_path}/reorder",
            json={
                "starting_revision": plan["photo_revision"],
                "photo_ids": [original[1]["id"], original[0]["id"]],
            },
        )
        reordered_plan = reordered.json()["daily_plans"][0]
        removed = await client.request(
            "DELETE",
            f"{collection_path}/{original[1]['id']}",
            json={
                "starting_revision": reordered_plan["photo_revision"],
            },
        )
        stale_removal = await client.request(
            "DELETE",
            f"{collection_path}/{original[1]['id']}",
            json={"starting_revision": reordered_plan["photo_revision"]},
        )

    assert first.status_code == 201
    assert second.status_code == 201
    assert [photo["position"] for photo in original] == [0, 1]
    assert len({photo["id"] for photo in original}) == 2
    assert [photo["id"] for photo in reordered_plan["photos"]] == [
        original[1]["id"],
        original[0]["id"],
    ]
    assert [photo["position"] for photo in reordered_plan["photos"]] == [0, 1]
    assert removed.status_code == 200
    assert stale_removal.status_code == 409
    assert stale_removal.json()["error"]["code"] == (
        "photo_collection_revision_conflict"
    )
    assert [photo["id"] for photo in removed.json()["daily_plans"][0]["photos"]] == [
        original[0]["id"]
    ]


async def test_photo_writes_reject_invalid_stale_and_unauthorized_changes_atomically(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        trip_id = (await client.post("/api/trips", json=TRIP)).json()["id"]
        detail = (await client.get(f"/api/trips/{trip_id}")).json()
        with_plan = await client.put(
            f"/api/trips/{trip_id}/daily-plans/2027-06-10",
            json={
                "starting_revision": detail["content_revision"],
                "destination_id": detail["destinations"][0]["id"],
                "title": "Arrival",
                "summary": "",
                "background_image": "",
            },
        )
        plan = with_plan.json()["daily_plans"][0]
        path = f"/api/trips/{trip_id}/daily-plans/{plan['id']}/photos"
        invalid = await client.post(
            path,
            json={
                "starting_revision": plan["photo_revision"],
                "url": "http://images.example/insecure.jpg",
                "caption": "Unsafe",
            },
        )
        created = await client.post(
            path,
            json={
                "starting_revision": plan["photo_revision"],
                "url": "https://images.example/safe.jpg",
                "caption": "Safe",
            },
        )
        stale = await client.post(
            path,
            json={
                "starting_revision": plan["photo_revision"],
                "url": "https://images.example/stale.jpg",
                "caption": "Stale",
            },
        )
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=JAMIE_ID,
            display_name="Jamie Traveller",
            role="traveller",
        )
        user["id"] = JAMIE_ID
        forbidden = await client.post(
            path,
            json={
                "starting_revision": created.json()["daily_plans"][0]["photo_revision"],
                "url": "https://images.example/forbidden.jpg",
                "caption": "Forbidden",
            },
        )
        unchanged = await client.get(f"/api/trips/{trip_id}")

    assert invalid.status_code == 422
    assert created.status_code == 201
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "photo_collection_revision_conflict"
    assert forbidden.status_code == 403
    assert [photo["url"] for photo in unchanged.json()["daily_plans"][0]["photos"]] == [
        "https://images.example/safe.jpg"
    ]


async def test_signed_in_user_creates_trip_and_finds_it_in_my_trips(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        created = await client.post("/api/trips", json=TRIP)
        listed = await client.get("/api/me/trips")

    assert created.status_code == 201
    assert listed.status_code == 200
    assert listed.json() == [
        {
            "id": created.json()["id"],
            "name": "Greek Islands 2027",
            "destination": "Cyclades",
            "short_name": "Greek Islands",
            "start_date": "2027-06-10",
            "end_date": "2027-06-17",
            "role": "creator",
        }
    ]


async def test_signed_in_user_can_create_multiple_independent_trips(
    database_settings: Settings,
) -> None:
    second_trip = {
        **TRIP,
        "name": "Japan 2028",
        "destination": "Tokyo",
        "short_name": "Japan",
        "start_date": "2028-04-01",
        "end_date": "2028-04-03",
    }

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        first = await client.post("/api/trips", json=TRIP)
        second = await client.post("/api/trips", json=second_trip)
        listed = await client.get("/api/me/trips")

    assert [first.status_code, second.status_code, listed.status_code] == [
        201,
        201,
        200,
    ]
    assert {(trip["name"], trip["role"]) for trip in listed.json()} == {
        ("Greek Islands 2027", "creator"),
        ("Japan 2028", "creator"),
    }
    assert first.json()["id"] != second.json()["id"]


async def test_trip_creation_rejects_client_supplied_creator_and_role(
    database_settings: Settings,
) -> None:
    untrusted_trip = {**TRIP, "creatorId": JAMIE_ID, "role": "creator"}

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        response = await client.post("/api/trips", json=untrusted_trip)
        listed = await client.get("/api/me/trips")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed",
        }
    }
    assert listed.json() == []


async def test_trip_creation_allows_optional_details_to_be_omitted(
    database_settings: Settings,
) -> None:
    minimal_trip = {
        "name": "Athens weekend",
        "destination": "Athens",
        "timezone": "Europe/Athens",
        "start_date": "2027-09-03",
        "end_date": "2027-09-05",
    }

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        response = await client.post("/api/trips", json=minimal_trip)
        detail = await client.get(f"/api/trips/{response.json()['id']}")

    assert response.status_code == 201
    assert detail.status_code == 200
    assert detail.json()["short_name"] == ""
    assert detail.json()["description"] == ""
    assert detail.json()["location"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", "   "), ("destination", "\t"), ("timezone", "Mars/Olympus")],
)
async def test_trip_creation_rejects_invalid_required_metadata(
    database_settings: Settings,
    field: str,
    value: str,
) -> None:
    invalid_trip = {**TRIP, field: value}

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        response = await client.post("/api/trips", json=invalid_trip)

    assert response.status_code == 422


async def test_trip_management_requires_authentication(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings):
        create_response = await client.post("/api/trips", json=TRIP)
        list_response = await client.get("/api/me/trips")

    assert [create_response.status_code, list_response.status_code] == [401, 401]
    assert create_response.json() == {
        "error": {
            "code": "authentication_required",
            "message": "Authentication required",
        }
    }


async def test_my_trips_is_scoped_to_the_authenticated_user(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        await client.post("/api/trips", json=TRIP)
        user["id"] = JAMIE_ID
        listed = await client.get("/api/me/trips")

    assert listed.status_code == 200
    assert listed.json() == []


async def test_created_trip_survives_a_new_application_instance(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        assert created.status_code == 201

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        listed = await client.get("/api/me/trips")

    assert listed.status_code == 200
    assert [(trip["name"], trip["role"]) for trip in listed.json()] == [
        ("Greek Islands 2027", "creator")
    ]


async def test_created_draft_is_available_only_to_its_participants(
    database_settings: Settings,
) -> None:
    async for client, app in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        participant_trip = await client.get(f"/api/trips/{created.json()['id']}")
        app.dependency_overrides.pop(require_current_user)
        anonymous_trip = await client.get(f"/api/trips/{created.json()['id']}")

    assert participant_trip.status_code == 200
    assert participant_trip.json()["name"] == "Greek Islands 2027"
    assert participant_trip.json()["calendar"] == [
        {"date": f"2027-06-{day:02d}", "day_number": day - 9, "is_planned": False}
        for day in range(10, 18)
    ]
    assert participant_trip.json()["roster"] == [
        {"display_name": "Test User", "role": "creator"}
    ]
    assert anonymous_trip.status_code == 401


async def test_creator_updates_trip_details_and_ordered_destinations(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        before = await client.get(f"/api/trips/{created.json()['id']}")
        cyclades_id = before.json()["destinations"][0]["id"]

        updated = await client.put(
            f"/api/trips/{created.json()['id']}/details",
            json={
                "starting_revision": before.json()["revision"],
                "name": "Aegean summer",
                "short_name": "Aegean",
                "description": "Athens first, then the islands.",
                "start_date": "2027-06-08",
                "end_date": "2027-06-19",
                "destinations": [
                    {
                        "name": "Athens",
                        "timezone": "Europe/Athens",
                        "location": {"lat": 37.9838, "lng": 23.7275},
                    },
                    {
                        "id": cyclades_id,
                        "name": "Cyclades",
                        "timezone": "Europe/Athens",
                        "location": {"lat": 37.4467, "lng": 25.3289},
                    },
                ],
            },
        )
        reader_projection = await client.get(f"/api/trips/{created.json()['id']}")

    assert updated.status_code == 200
    assert updated.json()["role"] == "creator"
    assert updated.json()["name"] == "Aegean summer"
    assert updated.json()["destination"] == "Athens"
    assert updated.json()["start_date"] == "2027-06-08"
    assert updated.json()["end_date"] == "2027-06-19"
    assert [destination["name"] for destination in updated.json()["destinations"]] == [
        "Athens",
        "Cyclades",
    ]
    assert updated.json()["destinations"][1]["id"] == cyclades_id
    assert reader_projection.json() == updated.json()


async def test_contributor_can_edit_but_traveller_cannot(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        created = await client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        original = await client.get(f"/api/trips/{trip_id}")
        destination = original.json()["destinations"][0]
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=JAMIE_ID,
            display_name="Jamie Contributor",
            role="contributor",
        )
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=MORGAN_ID,
            display_name="Morgan Traveller",
            role="traveller",
        )
        request = {
            "starting_revision": original.json()["revision"],
            "name": "Contributor update",
            "short_name": "Greek Islands",
            "description": "Updated together.",
            "start_date": "2027-06-10",
            "end_date": "2027-06-17",
            "destinations": [
                {
                    "id": destination["id"],
                    "name": destination["name"],
                    "timezone": destination["timezone"],
                    "location": destination["location"],
                }
            ],
        }

        user["id"] = JAMIE_ID
        contributor_update = await client.put(
            f"/api/trips/{trip_id}/details", json=request
        )
        user["id"] = MORGAN_ID
        traveller_update = await client.put(
            f"/api/trips/{trip_id}/details",
            json={**request, "name": "Traveller overwrite"},
        )
        traveller_view = await client.get(f"/api/trips/{trip_id}")

    assert contributor_update.status_code == 200
    assert contributor_update.json()["role"] == "contributor"
    assert traveller_update.status_code == 403
    assert traveller_update.json() == {
        "error": {
            "code": "trip_edit_forbidden",
            "message": "Trip editing is not permitted",
        }
    }
    assert traveller_view.json()["name"] == "Contributor update"
    assert traveller_view.json()["role"] == "traveller"


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "   "},
        {"destinations": []},
        {"destinations": [{"name": "Athens", "timezone": "Mars/Olympus"}]},
        {"start_date": "2027-06-18", "end_date": "2027-06-17"},
    ],
)
async def test_trip_details_reject_invalid_metadata(
    database_settings: Settings,
    changes: dict[str, object],
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        detail = await client.get(f"/api/trips/{created.json()['id']}")
        request: dict[str, object] = {
            "starting_revision": detail.json()["revision"],
            "name": detail.json()["name"],
            "short_name": detail.json()["short_name"],
            "description": detail.json()["description"],
            "start_date": detail.json()["start_date"],
            "end_date": detail.json()["end_date"],
            "destinations": [
                {
                    "id": destination["id"],
                    "name": destination["name"],
                    "timezone": destination["timezone"],
                    "location": destination["location"],
                }
                for destination in detail.json()["destinations"]
            ],
        }
        response = await client.put(
            f"/api/trips/{created.json()['id']}/details",
            json={**request, **changes},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_date_range_cannot_exclude_a_populated_daily_plan(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        detail = await client.get(f"/api/trips/{trip_id}")
        destination = detail.json()["destinations"][0]
        await add_daily_plan(
            database_settings,
            trip_id=trip_id,
            destination_id=destination["id"],
            plan_date="2027-06-10",
        )
        rejected = await client.put(
            f"/api/trips/{trip_id}/details",
            json={
                "starting_revision": detail.json()["revision"],
                "name": detail.json()["name"],
                "short_name": detail.json()["short_name"],
                "description": detail.json()["description"],
                "start_date": "2027-06-11",
                "end_date": detail.json()["end_date"],
                "destinations": [
                    {
                        "id": destination["id"],
                        "name": destination["name"],
                        "timezone": destination["timezone"],
                        "location": destination["location"],
                    }
                ],
            },
        )
        unchanged = await client.get(f"/api/trips/{trip_id}")

    assert rejected.status_code == 409
    assert rejected.json() == {
        "error": {
            "code": "trip_date_range_excludes_plans",
            "message": "Move or clear plans outside the new date range first",
        }
    }
    assert unchanged.json()["start_date"] == "2027-06-10"


async def test_destination_used_by_a_timeline_entry_cannot_be_removed(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        detail = await client.get(f"/api/trips/{trip_id}")
        cyclades = detail.json()["destinations"][0]
        with_athens = await client.put(
            f"/api/trips/{trip_id}/details",
            json={
                "starting_revision": detail.json()["revision"],
                "name": detail.json()["name"],
                "short_name": detail.json()["short_name"],
                "description": detail.json()["description"],
                "start_date": detail.json()["start_date"],
                "end_date": detail.json()["end_date"],
                "destinations": [
                    {
                        "id": cyclades["id"],
                        "name": cyclades["name"],
                        "timezone": cyclades["timezone"],
                        "location": cyclades["location"],
                    },
                    {"name": "Athens", "timezone": "Europe/Athens"},
                ],
            },
        )
        athens = with_athens.json()["destinations"][1]
        plan_id = await add_daily_plan(
            database_settings,
            trip_id=trip_id,
            destination_id=cyclades["id"],
            plan_date="2027-06-10",
        )
        await add_timeline_entry(
            database_settings,
            daily_plan_id=plan_id,
            destination_id=athens["id"],
        )
        rejected = await client.put(
            f"/api/trips/{trip_id}/details",
            json={
                "starting_revision": with_athens.json()["revision"],
                "name": detail.json()["name"],
                "short_name": detail.json()["short_name"],
                "description": detail.json()["description"],
                "start_date": detail.json()["start_date"],
                "end_date": detail.json()["end_date"],
                "destinations": [
                    {
                        "id": cyclades["id"],
                        "name": cyclades["name"],
                        "timezone": cyclades["timezone"],
                        "location": cyclades["location"],
                    }
                ],
            },
        )

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "trip_destination_in_use"


async def test_stale_trip_details_update_is_rejected_with_latest_values(
    database_settings: Settings,
) -> None:
    async for setup_client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await setup_client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        detail = await setup_client.get(f"/api/trips/{trip_id}")
        cyclades = detail.json()["destinations"][0]
        with_athens = await setup_client.put(
            f"/api/trips/{trip_id}/details",
            json={
                "starting_revision": detail.json()["revision"],
                "name": detail.json()["name"],
                "short_name": detail.json()["short_name"],
                "description": detail.json()["description"],
                "start_date": detail.json()["start_date"],
                "end_date": detail.json()["end_date"],
                "destinations": [
                    {
                        "id": cyclades["id"],
                        "name": cyclades["name"],
                        "timezone": cyclades["timezone"],
                        "location": cyclades["location"],
                    },
                    {"name": "Athens", "timezone": "Europe/Athens"},
                ],
            },
        )
    destinations = [
        {
            "id": destination["id"],
            "name": destination["name"],
            "timezone": destination["timezone"],
            "location": destination["location"],
        }
        for destination in with_athens.json()["destinations"]
    ]
    base_request = {
        "starting_revision": with_athens.json()["revision"],
        "name": detail.json()["name"],
        "short_name": detail.json()["short_name"],
        "description": detail.json()["description"],
        "start_date": detail.json()["start_date"],
        "end_date": detail.json()["end_date"],
    }
    app = create_app(database_settings)
    app.dependency_overrides[require_current_user] = lambda: AuthenticatedUser(
        id=UUID(ALEX_ID),
        session_id=UUID("00000000-0000-0000-0000-000000000001"),
        email="test@example.com",
        display_name="Test User",
    )
    async with (
        LifespanManager(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as first,
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as second,
    ):
        responses = await asyncio.gather(
            first.put(
                f"/api/trips/{trip_id}/details",
                json={**base_request, "destinations": destinations},
            ),
            second.put(
                f"/api/trips/{trip_id}/details",
                json={**base_request, "destinations": list(reversed(destinations))},
            ),
        )
        final = await first.get(f"/api/trips/{trip_id}")

    assert sorted(response.status_code for response in responses) == [200, 409]
    saved = next(response for response in responses if response.status_code == 200)
    rejected = next(response for response in responses if response.status_code == 409)
    assert rejected.json()["error"]["code"] == "trip_revision_conflict"
    assert rejected.json()["error"]["latest_values"] == saved.json()
    assert final.json() == saved.json()


async def test_every_participant_role_reads_the_draft_and_current_roster(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        created = await client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=JAMIE_ID,
            display_name="Jamie Contributor",
            role="contributor",
        )
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=MORGAN_ID,
            display_name="Morgan Traveller",
            role="traveller",
        )

        responses = []
        for account_id in (ALEX_ID, JAMIE_ID, MORGAN_ID):
            user["id"] = account_id
            responses.append(await client.get(f"/api/trips/{trip_id}"))

    assert [response.status_code for response in responses] == [200, 200, 200]
    expected_roster = [
        {"display_name": "Test User", "role": "creator"},
        {"display_name": "Jamie Contributor", "role": "contributor"},
        {"display_name": "Morgan Traveller", "role": "traveller"},
    ]
    assert all(response.json()["roster"] == expected_roster for response in responses)


async def test_created_draft_is_hidden_from_a_different_signed_in_user(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        created = await client.post("/api/trips", json=TRIP)
        user["id"] = JAMIE_ID
        hidden_trip = await client.get(f"/api/trips/{created.json()['id']}")

    assert hidden_trip.status_code == 404
    assert hidden_trip.json() == {
        "error": {"code": "trip_not_found", "message": "Trip not found"}
    }


async def test_participation_in_another_trip_does_not_reveal_a_draft(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        private_trip = await client.post("/api/trips", json=TRIP)

    async for client, _ in app_client(database_settings, {"id": JAMIE_ID}):
        other_trip = await client.post(
            "/api/trips",
            json={**TRIP, "name": "Jamie's Trip"},
        )
        hidden_trip = await client.get(f"/api/trips/{private_trip.json()['id']}")

    assert other_trip.status_code == 201
    assert hidden_trip.status_code == 404


async def test_membership_changes_apply_to_the_next_protected_request(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        created = await client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=JAMIE_ID,
            display_name="Jamie Former Participant",
            role="traveller",
        )

        user["id"] = JAMIE_ID
        accepted_participant = await client.get(f"/api/trips/{trip_id}")
        await remove_participant(
            database_settings,
            trip_id=trip_id,
            account_id=JAMIE_ID,
        )
        former_participant = await client.get(f"/api/trips/{trip_id}")

        user["id"] = ALEX_ID
        current_roster = await client.get(f"/api/trips/{trip_id}")

    assert accepted_participant.status_code == 200
    assert former_participant.status_code == 404
    assert current_roster.json()["roster"] == [
        {"display_name": "Test User", "role": "creator"}
    ]


async def test_unexpected_errors_are_logged_without_exposing_details(
    database_settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(database_settings)

    @app.get("/api/test/unexpected")
    async def unexpected() -> None:
        raise RuntimeError("private failure detail")

    with caplog.at_level("ERROR"):
        async with (
            LifespanManager(app),
            AsyncClient(
                transport=ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client,
        ):
            response = await client.get("/api/test/unexpected")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "An unexpected error occurred",
        }
    }
    assert "Unhandled request error" in caplog.text
    assert "private failure detail" not in response.text
