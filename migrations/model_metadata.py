from sqlalchemy import MetaData

from tripper_api.auth import auth_model  # noqa: F401
from tripper_api.core.models import Base
from tripper_api.destination import destination_model  # noqa: F401
from tripper_api.itinerary import (
    itinerary_daily_plan_model,  # noqa: F401
    itinerary_photo_model,  # noqa: F401
    itinerary_stay_model,  # noqa: F401
    itinerary_timeline_model,  # noqa: F401
)
from tripper_api.membership import membership_model  # noqa: F401
from tripper_api.trip import trip_model  # noqa: F401

target_metadata: MetaData = Base.metadata
