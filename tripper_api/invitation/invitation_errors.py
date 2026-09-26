class InvitationForbiddenError(Exception):
    pass


class InvitationNotFoundError(Exception):
    pass


class ActiveInvitationExistsError(Exception):
    pass


class InvalidDeliveryWebhookError(Exception):
    pass
