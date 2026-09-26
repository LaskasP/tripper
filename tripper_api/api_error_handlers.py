from fastapi import FastAPI

from tripper_api.auth.auth_error_handler import register_auth_error_handlers
from tripper_api.core.error_handler import register_error_handlers
from tripper_api.destination.destination_error_handler import (
    register_destination_error_handlers,
)
from tripper_api.itinerary.itinerary_error_handler import (
    register_itinerary_error_handlers,
)
from tripper_api.trip.trip_error_handler import register_trip_error_handlers


def register_api_error_handlers(app: FastAPI) -> None:
    register_error_handlers(app)
    register_auth_error_handlers(app)
    register_destination_error_handlers(app)
    register_trip_error_handlers(app)
    register_itinerary_error_handlers(app)
