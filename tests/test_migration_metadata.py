from sqlalchemy import CheckConstraint, UniqueConstraint, inspect

from migrations.model_metadata import target_metadata
from tripper_api.destination.destination_model import Destination
from tripper_api.itinerary.itinerary_daily_plan_model import DailyPlan
from tripper_api.itinerary.itinerary_photo_model import Photo
from tripper_api.itinerary.itinerary_stay_model import Stay
from tripper_api.itinerary.itinerary_timeline_model import TimelineEntry
from tripper_api.membership.membership_model import TripMembership
from tripper_api.trip.trip_model import Trip


def test_migration_metadata_registers_every_model_in_its_owning_module() -> None:
    expected_models = {
        "trips": Trip,
        "destinations": Destination,
        "trip_memberships": TripMembership,
        "daily_plans": DailyPlan,
        "timeline_entries": TimelineEntry,
        "stays": Stay,
        "photos": Photo,
    }

    assert {"accounts", "sessions", *expected_models} == set(target_metadata.tables)
    assert {
        table_name: model.__module__ for table_name, model in expected_models.items()
    } == {
        "trips": "tripper_api.trip.trip_model",
        "destinations": "tripper_api.destination.destination_model",
        "trip_memberships": "tripper_api.membership.membership_model",
        "daily_plans": "tripper_api.itinerary.itinerary_daily_plan_model",
        "timeline_entries": "tripper_api.itinerary.itinerary_timeline_model",
        "stays": "tripper_api.itinerary.itinerary_stay_model",
        "photos": "tripper_api.itinerary.itinerary_photo_model",
    }


def test_moved_table_metadata_preserves_columns_constraints_and_indexes() -> None:
    expected_columns = {
        "trips": {
            "id",
            "name",
            "short_name",
            "description",
            "start_date",
            "end_date",
            "revision",
            "content_revision",
            "created_at",
        },
        "destinations": {
            "id",
            "trip_id",
            "name",
            "timezone",
            "latitude",
            "longitude",
            "position",
            "revision",
        },
        "trip_memberships": {"id", "trip_id", "account_id", "role", "revision"},
        "daily_plans": {
            "id",
            "trip_id",
            "destination_id",
            "date",
            "title",
            "summary",
            "background_image",
            "revision",
            "timeline_revision",
            "photo_revision",
        },
        "timeline_entries": {
            "id",
            "daily_plan_id",
            "destination_id",
            "local_time",
            "title",
            "description",
            "location_name",
            "latitude",
            "longitude",
            "position",
            "revision",
        },
        "stays": {
            "id",
            "daily_plan_id",
            "name",
            "address",
            "latitude",
            "longitude",
            "check_in",
            "check_out",
            "public_listing_url",
            "booking_platform",
            "revision",
        },
        "photos": {"id", "daily_plan_id", "url", "caption", "position", "revision"},
    }
    expected_column_signatures = {
        "trips": {
            "id": ("UUID", False, True, None),
            "name": ("VARCHAR(200)", False, False, None),
            "short_name": ("VARCHAR(80)", False, False, None),
            "description": ("TEXT", False, False, None),
            "start_date": ("DATE", False, False, None),
            "end_date": ("DATE", False, False, None),
            "revision": ("INTEGER", False, False, "1"),
            "content_revision": ("INTEGER", False, False, "1"),
            "created_at": ("DATETIME", False, False, "CURRENT_TIMESTAMP"),
        },
        "destinations": {
            "id": ("UUID", False, True, None),
            "trip_id": ("UUID", False, False, None),
            "name": ("VARCHAR(200)", False, False, None),
            "timezone": ("VARCHAR(100)", False, False, None),
            "latitude": ("FLOAT", True, False, None),
            "longitude": ("FLOAT", True, False, None),
            "position": ("INTEGER", False, False, None),
            "revision": ("INTEGER", False, False, "1"),
        },
        "trip_memberships": {
            "id": ("UUID", False, True, None),
            "trip_id": ("UUID", False, False, None),
            "account_id": ("UUID", False, False, None),
            "role": ("VARCHAR(20)", False, False, None),
            "revision": ("INTEGER", False, False, "1"),
        },
        "daily_plans": {
            "id": ("UUID", False, True, None),
            "trip_id": ("UUID", False, False, None),
            "destination_id": ("UUID", False, False, None),
            "date": ("DATE", False, False, None),
            "title": ("VARCHAR(200)", False, False, None),
            "summary": ("TEXT", False, False, None),
            "background_image": ("TEXT", False, False, None),
            "revision": ("INTEGER", False, False, "1"),
            "timeline_revision": ("INTEGER", False, False, "1"),
            "photo_revision": ("INTEGER", False, False, "1"),
        },
        "timeline_entries": {
            "id": ("UUID", False, True, None),
            "daily_plan_id": ("UUID", False, False, None),
            "destination_id": ("UUID", True, False, None),
            "local_time": ("TIME", False, False, None),
            "title": ("VARCHAR(200)", False, False, None),
            "description": ("TEXT", False, False, None),
            "location_name": ("VARCHAR(300)", True, False, None),
            "latitude": ("FLOAT", True, False, None),
            "longitude": ("FLOAT", True, False, None),
            "position": ("INTEGER", False, False, None),
            "revision": ("INTEGER", False, False, "1"),
        },
        "stays": {
            "id": ("UUID", False, True, None),
            "daily_plan_id": ("UUID", False, False, None),
            "name": ("VARCHAR(200)", False, False, None),
            "address": ("TEXT", False, False, None),
            "latitude": ("FLOAT", True, False, None),
            "longitude": ("FLOAT", True, False, None),
            "check_in": ("TIME", True, False, None),
            "check_out": ("TIME", True, False, None),
            "public_listing_url": ("TEXT", True, False, None),
            "booking_platform": ("VARCHAR(80)", True, False, None),
            "revision": ("INTEGER", False, False, "1"),
        },
        "photos": {
            "id": ("UUID", False, True, None),
            "daily_plan_id": ("UUID", False, False, None),
            "url": ("TEXT", False, False, None),
            "caption": ("TEXT", False, False, None),
            "position": ("INTEGER", False, False, None),
            "revision": ("INTEGER", False, False, "1"),
        },
    }
    expected_named_constraints = {
        "trips": {
            "valid_trip_date_range",
            "positive_trip_revision",
            "positive_trip_content_revision",
        },
        "destinations": {
            "nonnegative_destination_position",
            "complete_destination_location",
            "positive_destination_revision",
            "uq_destination_trip_position",
        },
        "trip_memberships": {
            "valid_membership_role",
            "positive_membership_revision",
            "uq_membership_trip_account",
        },
        "daily_plans": {
            "positive_daily_plan_revision",
            "positive_timeline_collection_revision",
            "positive_photo_collection_revision",
            "uq_daily_plan_trip_date",
        },
        "timeline_entries": {
            "complete_timeline_entry_location",
            "nonnegative_timeline_position",
            "positive_timeline_revision",
            "uq_timeline_daily_plan_position",
        },
        "stays": {
            "complete_stay_location",
            "positive_stay_revision",
            "uq_stay_daily_plan",
        },
        "photos": {
            "nonnegative_photo_position",
            "positive_photo_revision",
            "uq_photo_daily_plan_position",
        },
    }

    for table_name, columns in expected_columns.items():
        table = target_metadata.tables[table_name]
        assert set(table.columns.keys()) == columns
        assert {
            column.name: (
                str(column.type),
                column.nullable,
                column.primary_key,
                None
                if column.server_default is None
                else str(column.server_default.arg),
            )
            for column in table.columns
        } == expected_column_signatures[table_name]
        assert {
            constraint.name
            for constraint in table.constraints
            if isinstance(constraint, (CheckConstraint, UniqueConstraint))
        } == expected_named_constraints[table_name]

    membership = target_metadata.tables["trip_memberships"]
    assert {index.name for index in membership.indexes} == {"uq_membership_one_creator"}
    assert list(membership.c.role.type.enums) == [
        "creator",
        "contributor",
        "traveller",
    ]


def test_moved_table_metadata_preserves_important_foreign_keys() -> None:
    expected_foreign_keys = {
        "destinations": {"trip_id": (None, "trips.id", "CASCADE")},
        "trip_memberships": {
            "trip_id": (None, "trips.id", "CASCADE"),
            "account_id": ("fk_membership_account", "accounts.id", None),
        },
        "daily_plans": {
            "trip_id": (None, "trips.id", "CASCADE"),
            "destination_id": (None, "destinations.id", "RESTRICT"),
        },
        "timeline_entries": {
            "daily_plan_id": (None, "daily_plans.id", "CASCADE"),
            "destination_id": (None, "destinations.id", "RESTRICT"),
        },
        "stays": {"daily_plan_id": (None, "daily_plans.id", "CASCADE")},
        "photos": {"daily_plan_id": (None, "daily_plans.id", "CASCADE")},
    }

    for table_name, expected in expected_foreign_keys.items():
        table = target_metadata.tables[table_name]
        actual = {
            foreign_key.parent.name: (
                foreign_key.constraint.name,
                foreign_key.target_fullname,
                foreign_key.ondelete,
            )
            for foreign_key in table.foreign_keys
        }
        assert actual == expected


def test_guide_relationships_are_explicit_and_forbid_implicit_lazy_loading() -> None:
    trip_relationships = inspect(Trip).relationships
    plan_relationships = inspect(DailyPlan).relationships

    assert set(trip_relationships.keys()) == {"destinations", "daily_plans"}
    assert set(plan_relationships.keys()) == {"timeline_entries", "stay", "photos"}
    assert all(
        relationship.lazy == "raise"
        for relationship in [*trip_relationships, *plan_relationships]
    )
    assert all(
        relationship.passive_deletes == "all"
        for relationship in [*trip_relationships, *plan_relationships]
    )

    assert not inspect(TripMembership).relationships
    assert not inspect(Destination).relationships
