from sqlalchemy import MetaData

from tripper_api.auth import auth_model  # noqa: F401
from tripper_api.core.models import Base
from tripper_api.trip import trip_model  # noqa: F401

target_metadata: MetaData = Base.metadata
