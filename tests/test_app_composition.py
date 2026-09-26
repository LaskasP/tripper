import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tripper_api.app import create_app
from tripper_api.auth.auth_error_handler import register_auth_error_handlers
from tripper_api.auth.auth_errors import (
    AuthenticationRequiredError,
    CsrfValidationError,
    InvalidGoogleCredentialError,
)
from tripper_api.core.config import Settings
from tripper_api.core.error_handler import register_error_handlers
from tripper_api.destination.destination_error_handler import (
    register_destination_error_handlers,
)
from tripper_api.destination.destination_errors import (
    TripDestinationInUseError,
    TripDestinationMismatchError,
)
from tripper_api.invitation.invitation_error_handler import (
    register_invitation_error_handlers,
)
from tripper_api.invitation.invitation_errors import (
    ActiveInvitationExistsError,
    InvalidDeliveryWebhookError,
    InvitationForbiddenError,
    InvitationNotFoundError,
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
from tripper_api.publication.publication_error_handler import (
    register_publication_error_handlers,
)
from tripper_api.publication.publication_errors import (
    PublicationForbiddenError,
    PublicationRevisionConflictError,
    TripNotReadyToPublishError,
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


def test_publication_error_handlers_are_registered_by_the_publication_feature() -> None:
    app = FastAPI()

    register_publication_error_handlers(app)

    assert PublicationForbiddenError in app.exception_handlers
    assert TripNotReadyToPublishError in app.exception_handlers
    assert PublicationRevisionConflictError in app.exception_handlers


def test_invitation_error_handlers_are_registered_by_the_invitation_feature() -> None:
    app = FastAPI()

    register_invitation_error_handlers(app)

    assert InvitationForbiddenError in app.exception_handlers
    assert InvitationNotFoundError in app.exception_handlers
    assert ActiveInvitationExistsError in app.exception_handlers
    assert InvalidDeliveryWebhookError in app.exception_handlers


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
    app = create_app(
        Settings(
            database_url=(
                "postgresql+psycopg_async://tripper:secret@localhost/tripper"
            ),
            invitation_token_key=("--GlAsI7zn2JODd7UGI2F-oaV8iSIoNlxyMGtGSshps="),
        )
    )

    api_routes = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }
    assert api_routes == {
        ("GET", "/api/config"),
        ("GET", "/api/auth/google/config"),
        ("POST", "/api/auth/google"),
        ("GET", "/api/auth/session"),
        ("POST", "/api/auth/sign-out"),
        ("GET", "/api/me/trips"),
        ("POST", "/api/email/mailgun/events"),
        ("GET", "/api/trips/{trip_id}/invitations"),
        ("POST", "/api/trips/{trip_id}/invitations"),
        ("DELETE", "/api/trips/{trip_id}/invitations/{invitation_id}"),
        ("POST", "/api/trips/{trip_id}/invitations/{invitation_id}/replace"),
        ("POST", "/api/trips"),
        ("GET", "/api/trips/{trip_id}"),
        ("GET", "/api/trips/{trip_id}/publication"),
        ("POST", "/api/trips/{trip_id}/publication"),
        ("DELETE", "/api/trips/{trip_id}/publication"),
        ("POST", "/api/trips/{trip_id}/publication/rotate"),
        ("GET", "/api/public-guides/{public_token}"),
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
        PublicationForbiddenError,
        TripNotReadyToPublishError,
        PublicationRevisionConflictError,
        InvitationForbiddenError,
        InvitationNotFoundError,
        ActiveInvitationExistsError,
        InvalidDeliveryWebhookError,
    }
    assert feature_errors <= app.exception_handlers.keys()


def test_disabled_invitation_feature_is_absent_from_the_api_surface() -> None:
    settings = Settings(
        database_url="postgresql+psycopg_async://tripper:secret@localhost/tripper",
        invitations_enabled=False,
    )

    app = create_app(settings)

    paths = app.openapi()["paths"]
    assert "/api/config" in paths
    assert not any("invitations" in path for path in paths)
    assert "/api/email/mailgun/events" not in paths


@pytest.mark.asyncio(loop_factories=["selector"])
async def test_application_config_exposes_disabled_invitations(
    database_settings: Settings,
) -> None:
    settings = Settings(
        database_url=database_settings.database_url,
        invitations_enabled=False,
    )
    app = create_app(settings)

    async with LifespanManager(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/config")

    assert response.status_code == 200
    assert response.json() == {"invitations_enabled": False}


@pytest.mark.parametrize(
    ("exception", "expected_status", "expected_error"),
    [
        (
            AuthenticationRequiredError(),
            401,
            {
                "code": "authentication_required",
                "message": "Authentication required",
            },
        ),
        (
            CsrfValidationError(),
            403,
            {
                "code": "csrf_validation_failed",
                "message": "CSRF validation failed",
            },
        ),
        (
            InvalidGoogleCredentialError(),
            401,
            {
                "code": "invalid_google_credential",
                "message": "Google sign-in failed",
            },
        ),
        (
            TripDestinationMismatchError(),
            422,
            {
                "code": "trip_destination_mismatch",
                "message": "A destination does not belong to this Trip",
            },
        ),
        (
            TripDestinationInUseError(),
            409,
            {
                "code": "trip_destination_in_use",
                "message": "Move or clear plans using this destination first",
            },
        ),
        (
            TripNotFoundError(),
            404,
            {"code": "trip_not_found", "message": "Trip not found"},
        ),
        (
            TripEditForbiddenError(),
            403,
            {
                "code": "trip_edit_forbidden",
                "message": "Trip editing is not permitted",
            },
        ),
        (
            TripDateRangeExcludesPlansError(),
            409,
            {
                "code": "trip_date_range_excludes_plans",
                "message": "Move or clear plans outside the new date range first",
            },
        ),
        (
            TripRevisionConflictError({"revision": 2}),
            409,
            {
                "code": "trip_revision_conflict",
                "message": "This Trip changed after editing started",
                "latest_values": {"revision": 2},
            },
        ),
        (
            PublicationForbiddenError(),
            403,
            {
                "code": "publication_forbidden",
                "message": "Only the Trip Creator can manage publication",
            },
        ),
        (
            TripNotReadyToPublishError(),
            409,
            {
                "code": "trip_not_ready_to_publish",
                "message": "Complete valid Trip details and at least one Daily plan first",
            },
        ),
        (
            PublicationRevisionConflictError(),
            409,
            {
                "code": "publication_revision_conflict",
                "message": "Publication changed after this page loaded",
            },
        ),
        (
            InvitationForbiddenError(),
            403,
            {
                "code": "invitation_forbidden",
                "message": "Only the Trip Creator can manage invitations",
            },
        ),
        (
            InvitationNotFoundError(),
            404,
            {"code": "invitation_not_found", "message": "Invitation not found"},
        ),
        (
            ActiveInvitationExistsError(),
            409,
            {
                "code": "active_invitation_exists",
                "message": "An active invitation already exists for this email",
            },
        ),
        (
            InvalidDeliveryWebhookError(),
            401,
            {
                "code": "invalid_delivery_webhook",
                "message": "Invalid delivery webhook",
            },
        ),
        (
            DailyPlanNotFoundError(),
            404,
            {"code": "daily_plan_not_found", "message": "Daily plan not found"},
        ),
        (
            DailyPlanOccupiedError(),
            409,
            {
                "code": "daily_plan_occupied",
                "message": "Target date already has a plan",
            },
        ),
        (
            DailyPlanOutOfRangeError(),
            422,
            {
                "code": "daily_plan_out_of_range",
                "message": "Date is outside the Trip",
            },
        ),
        (
            DailyPlanRevisionConflictError({"revision": 3}),
            409,
            {
                "code": "daily_plan_revision_conflict",
                "message": "This Daily plan changed after editing started",
                "current_plan": {"revision": 3},
            },
        ),
        (
            StayNotFoundError(),
            404,
            {"code": "stay_not_found", "message": "Stay not found"},
        ),
        (
            StayRevisionConflictError({"revision": 4}),
            409,
            {
                "code": "stay_revision_conflict",
                "message": "This Stay changed after editing started",
                "current_stay": {"revision": 4},
            },
        ),
        (
            TimelineEntryNotFoundError(),
            404,
            {
                "code": "timeline_entry_not_found",
                "message": "Timeline entry not found",
            },
        ),
        (
            TimelineEntryRevisionConflictError({"revision": 5}),
            409,
            {
                "code": "timeline_entry_revision_conflict",
                "message": "This Timeline entry changed after editing started",
                "latest_values": {"revision": 5},
            },
        ),
        (
            TimelineCollectionRevisionConflictError({"revision": 6}),
            409,
            {
                "code": "timeline_collection_revision_conflict",
                "message": "This Timeline changed after editing started",
                "latest_values": {"revision": 6},
            },
        ),
        (
            TimelineOrderInvalidError(),
            422,
            {
                "code": "timeline_order_invalid",
                "message": (
                    "Timeline order must contain every entry in chronological order"
                ),
            },
        ),
        (
            PhotoNotFoundError(),
            404,
            {"code": "photo_not_found", "message": "Photo not found"},
        ),
        (
            PhotoCollectionRevisionConflictError({"revision": 7}),
            409,
            {
                "code": "photo_collection_revision_conflict",
                "message": "These photos changed after editing started",
                "latest_values": {"revision": 7},
            },
        ),
        (
            PhotoOrderInvalidError(),
            422,
            {
                "code": "photo_order_invalid",
                "message": "Photo order must contain every photo exactly once",
            },
        ),
    ],
)
@pytest.mark.asyncio(loop_factories=["selector"])
async def test_feature_error_handlers_preserve_the_public_envelope(
    exception: Exception,
    expected_status: int,
    expected_error: dict[str, object],
) -> None:
    app = FastAPI()
    register_auth_error_handlers(app)
    register_destination_error_handlers(app)
    register_trip_error_handlers(app)
    register_itinerary_error_handlers(app)
    register_publication_error_handlers(app)
    register_invitation_error_handlers(app)

    @app.get("/raise-feature-error")
    async def raise_feature_error() -> None:
        raise exception

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/raise-feature-error")

    assert response.status_code == expected_status
    assert response.json() == {"error": expected_error}
