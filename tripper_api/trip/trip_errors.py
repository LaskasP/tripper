class TripNotFoundError(Exception):
    pass


class TripEditForbiddenError(Exception):
    pass


class TripDateRangeExcludesPlansError(Exception):
    pass


class TripDestinationMismatchError(Exception):
    pass


class TripDestinationInUseError(Exception):
    pass


class TripRevisionConflictError(Exception):
    def __init__(self, latest_values: dict[str, object]) -> None:
        self.latest_values = latest_values


class DailyPlanNotFoundError(Exception):
    pass


class DailyPlanOccupiedError(Exception):
    pass


class DailyPlanOutOfRangeError(Exception):
    pass


class DailyPlanRevisionConflictError(Exception):
    def __init__(self, latest_values: dict[str, object]) -> None:
        self.latest_values = latest_values
