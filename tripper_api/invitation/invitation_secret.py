from base64 import urlsafe_b64encode
from hashlib import sha256
from hmac import new as hmac_new
from uuid import UUID


def derive_invitation_secret(invitation_id: UUID, token_key: bytes) -> str:
    digest = hmac_new(
        token_key,
        b"tripper-invitation-v1:" + invitation_id.bytes,
        sha256,
    ).digest()
    return urlsafe_b64encode(digest).rstrip(b"=").decode()
