class TripEditForbiddenError(Exception):
    pass


class TripDateRangeExcludesPlansError(Exception):
    pass


class TripRevisionConflictError(Exception):
    def __init__(self, latest_values: dict[str, object]) -> None:
        self.latest_values = latest_values
