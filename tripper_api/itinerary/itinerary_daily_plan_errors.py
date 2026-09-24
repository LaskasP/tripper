class DailyPlanNotFoundError(Exception):
    pass


class DailyPlanOccupiedError(Exception):
    pass


class DailyPlanOutOfRangeError(Exception):
    pass


class DailyPlanRevisionConflictError(Exception):
    def __init__(self, current_plan: dict[str, object] | None) -> None:
        self.current_plan = current_plan
