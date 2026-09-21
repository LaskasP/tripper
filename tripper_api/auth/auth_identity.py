from dataclasses import dataclass


@dataclass(frozen=True)
class GoogleIdentity:
    issuer: str
    subject: str
    email: str
    display_name: str
