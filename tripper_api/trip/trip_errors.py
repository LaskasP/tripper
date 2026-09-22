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
