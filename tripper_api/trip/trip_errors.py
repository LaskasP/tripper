class TripNotFoundError(Exception):
    pass


class PhotoNotFoundError(Exception):
    pass


class PhotoCollectionRevisionConflictError(Exception):
    def __init__(self, latest_values: dict[str, object]) -> None:
        self.latest_values = latest_values


class PhotoOrderInvalidError(Exception):
    pass
