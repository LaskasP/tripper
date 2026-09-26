from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from tripper_api.invitation.invitation_model import DeliveryEventType, OutboxStatus
from tripper_api.membership.membership_model import TripRole


@dataclass(frozen=True)
class InvitationSummary:
    id: UUID
    email: str
    role: TripRole
    created_at: datetime
    expires_at: datetime
    delivery_status: OutboxStatus


@dataclass(frozen=True)
class ClaimedInvitationEmail:
    outbox_id: UUID
    invitation_id: UUID
    recipient_email: str
    deduplication_key: str
    attempt_count: int


@dataclass(frozen=True)
class NormalizedDeliveryEvent:
    provider_event_id: str
    deduplication_key: str
    event_type: DeliveryEventType
    occurred_at: datetime
