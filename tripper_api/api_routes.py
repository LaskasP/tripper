from fastapi import FastAPI

from tripper_api.auth.auth_controller import router as auth_router
from tripper_api.itinerary.itinerary_daily_plan_controller import (
    router as daily_plan_router,
)
from tripper_api.itinerary.itinerary_photo_controller import router as photo_router
from tripper_api.itinerary.itinerary_stay_controller import router as stay_router
from tripper_api.itinerary.itinerary_timeline_controller import (
    router as timeline_router,
)
from tripper_api.membership.membership_controller import router as membership_router
from tripper_api.publication.publication_controller import router as publication_router
from tripper_api.trip.trip_command_controller import router as trip_command_router
from tripper_api.trip.trip_controller import router as trip_router


def register_api_routes(app: FastAPI) -> None:
    app.include_router(auth_router)
    app.include_router(membership_router)
    app.include_router(trip_command_router)
    app.include_router(daily_plan_router)
    app.include_router(stay_router)
    app.include_router(timeline_router)
    app.include_router(photo_router)
    app.include_router(publication_router)
    app.include_router(trip_router)
