class StayNotFoundError(Exception):
    pass


class StayRevisionConflictError(Exception):
    def __init__(self, current_stay: dict[str, object] | None) -> None:
        self.current_stay = current_stay
