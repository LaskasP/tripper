from fastapi import FastAPI

from tripper_api.app import create_app
from tripper_api.auth.auth_error_handler import register_auth_error_handlers
from tripper_api.auth.auth_errors import (
    AuthenticationRequiredError,
    CsrfValidationError,
    InvalidGoogleCredentialError,
)
from tripper_api.core.error_handler import register_error_handlers
from tripper_api.destination.destination_error_handler import (
    register_destination_error_handlers,
)
from tripper_api.destination.destination_errors import (
    TripDestinationInUseError,
    TripDestinationMismatchError,
)
from tripper_api.itinerary.itinerary_daily_plan_errors import (
    DailyPlanNotFoundError,
    DailyPlanOccupiedError,
    DailyPlanOutOfRangeError,
    DailyPlanRevisionConflictError,
)
from tripper_api.itinerary.itinerary_error_handler import (
    register_itinerary_error_handlers,
)
from tripper_api.itinerary.itinerary_photo_errors import (
    PhotoCollectionRevisionConflictError,
    PhotoNotFoundError,
    PhotoOrderInvalidError,
)
from tripper_api.itinerary.itinerary_stay_errors import (
    StayNotFoundError,
    StayRevisionConflictError,
)
from tripper_api.itinerary.itinerary_timeline_errors import (
    TimelineCollectionRevisionConflictError,
    TimelineEntryNotFoundError,
    TimelineEntryRevisionConflictError,
    TimelineOrderInvalidError,
)
from tripper_api.trip.trip_command_errors import (
    TripDateRangeExcludesPlansError,
    TripEditForbiddenError,
    TripRevisionConflictError,
)
from tripper_api.trip.trip_error_handler import register_trip_error_handlers
from tripper_api.trip.trip_errors import TripNotFoundError


def test_auth_error_handlers_are_registered_by_the_auth_feature() -> None:
    app = FastAPI()

    register_auth_error_handlers(app)

    assert AuthenticationRequiredError in app.exception_handlers
    assert CsrfValidationError in app.exception_handlers
    assert InvalidGoogleCredentialError in app.exception_handlers


def test_destination_error_handlers_are_registered_by_the_destination_feature() -> None:
    app = FastAPI()

    register_destination_error_handlers(app)

    assert TripDestinationMismatchError in app.exception_handlers
    assert TripDestinationInUseError in app.exception_handlers


def test_trip_error_handlers_are_registered_by_the_trip_feature() -> None:
    app = FastAPI()

    register_trip_error_handlers(app)

    assert TripNotFoundError in app.exception_handlers
    assert TripEditForbiddenError in app.exception_handlers
    assert TripDateRangeExcludesPlansError in app.exception_handlers
    assert TripRevisionConflictError in app.exception_handlers


def test_itinerary_error_handlers_are_registered_by_the_itinerary_feature() -> None:
    app = FastAPI()

    register_itinerary_error_handlers(app)

    expected_errors = {
        DailyPlanNotFoundError,
        DailyPlanOccupiedError,
        DailyPlanOutOfRangeError,
        DailyPlanRevisionConflictError,
        StayNotFoundError,
        StayRevisionConflictError,
        TimelineEntryNotFoundError,
        TimelineEntryRevisionConflictError,
        TimelineCollectionRevisionConflictError,
        TimelineOrderInvalidError,
        PhotoNotFoundError,
        PhotoCollectionRevisionConflictError,
        PhotoOrderInvalidError,
    }
    assert expected_errors <= app.exception_handlers.keys()


def test_core_error_handlers_do_not_register_feature_exceptions() -> None:
    app = FastAPI()

    register_error_handlers(app)

    feature_errors = {
        AuthenticationRequiredError,
        TripDestinationMismatchError,
        DailyPlanNotFoundError,
        TripNotFoundError,
    }
    assert feature_errors.isdisjoint(app.exception_handlers)


def test_app_factory_composes_every_feature_route_and_error_handler() -> None:
    app = create_app()

    api_routes = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }
    assert api_routes == {
        ("GET", "/api/auth/google/config"),
        ("POST", "/api/auth/google"),
        ("GET", "/api/auth/session"),
        ("POST", "/api/auth/sign-out"),
        ("GET", "/api/me/trips"),
        ("POST", "/api/trips"),
        ("GET", "/api/trips/{trip_id}"),
        ("PUT", "/api/trips/{trip_id}/details"),
        ("PUT", "/api/trips/{trip_id}/daily-plans/{plan_date}"),
        ("DELETE", "/api/trips/{trip_id}/daily-plans/{plan_date}"),
        ("POST", "/api/trips/{trip_id}/daily-plans/{plan_id}/move"),
        ("PUT", "/api/trips/{trip_id}/daily-plans/{plan_id}/stay"),
        ("DELETE", "/api/trips/{trip_id}/daily-plans/{plan_id}/stay"),
        ("POST", "/api/trips/{trip_id}/daily-plans/{plan_id}/timeline"),
        ("POST", "/api/trips/{trip_id}/daily-plans/{plan_id}/timeline/reorder"),
        (
            "POST",
            "/api/trips/{trip_id}/daily-plans/{plan_id}/timeline/{entry_id}/move",
        ),
        (
            "PUT",
            "/api/trips/{trip_id}/daily-plans/{plan_id}/timeline/{entry_id}",
        ),
        (
            "DELETE",
            "/api/trips/{trip_id}/daily-plans/{plan_id}/timeline/{entry_id}",
        ),
        ("POST", "/api/trips/{trip_id}/daily-plans/{plan_id}/photos"),
        ("POST", "/api/trips/{trip_id}/daily-plans/{plan_id}/photos/reorder"),
        (
            "DELETE",
            "/api/trips/{trip_id}/daily-plans/{plan_id}/photos/{photo_id}",
        ),
    }
    feature_errors = {
        AuthenticationRequiredError,
        CsrfValidationError,
        InvalidGoogleCredentialError,
        TripDestinationMismatchError,
        TripDestinationInUseError,
        DailyPlanNotFoundError,
        DailyPlanOccupiedError,
        DailyPlanOutOfRangeError,
        DailyPlanRevisionConflictError,
        StayNotFoundError,
        StayRevisionConflictError,
        TimelineEntryNotFoundError,
        TimelineEntryRevisionConflictError,
        TimelineCollectionRevisionConflictError,
        TimelineOrderInvalidError,
        PhotoNotFoundError,
        PhotoCollectionRevisionConflictError,
        PhotoOrderInvalidError,
        TripNotFoundError,
        TripEditForbiddenError,
        TripDateRangeExcludesPlansError,
        TripRevisionConflictError,
    }
    assert feature_errors <= app.exception_handlers.keys()
