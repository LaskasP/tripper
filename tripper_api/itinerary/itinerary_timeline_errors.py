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
