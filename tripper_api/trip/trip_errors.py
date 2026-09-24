class TripNotFoundError(Exception):
    pass


class DailyPlanNotFoundError(Exception):
    pass


class DailyPlanOccupiedError(Exception):
    pass


class DailyPlanOutOfRangeError(Exception):
    pass


class DailyPlanRevisionConflictError(Exception):
    def __init__(self, latest_values: dict[str, object]) -> None:
        self.latest_values = latest_values


class TimelineEntryNotFoundError(Exception):
    pass


class TimelineEntryRevisionConflictError(Exception):
    def __init__(self, latest_values: dict[str, object]) -> None:
        self.latest_values = latest_values


class TimelineCollectionRevisionConflictError(Exception):
    def __init__(self, latest_values: dict[str, object]) -> None:
        self.latest_values = latest_values


class TimelineOrderInvalidError(Exception):
    pass


class PhotoNotFoundError(Exception):
    pass


class StayNotFoundError(Exception):
    pass


class StayRevisionConflictError(Exception):
    def __init__(self, latest_values: dict[str, object]) -> None:
        self.latest_values = latest_values


class PhotoCollectionRevisionConflictError(Exception):
    def __init__(self, latest_values: dict[str, object]) -> None:
        self.latest_values = latest_values


class PhotoOrderInvalidError(Exception):
    pass
