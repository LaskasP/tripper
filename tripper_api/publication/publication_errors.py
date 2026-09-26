class PublicationForbiddenError(Exception):
    pass


class TripNotReadyToPublishError(Exception):
    pass


class PublicationRevisionConflictError(Exception):
    pass
