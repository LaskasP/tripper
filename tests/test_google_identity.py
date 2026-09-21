import json
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from tripper_api.auth.google_identity import (
    GOOGLE_CERTIFICATES_URL,
    GoogleIdentityVerifier,
    InvalidGoogleCredentialError,
)

pytestmark = pytest.mark.asyncio(loop_factories=["selector"])


def google_token(*, audience: str, issuer: str) -> tuple[str, dict[str, object]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "google-key-1", "use": "sig", "alg": "RS256"})
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": issuer,
            "aud": audience,
            "sub": "google-subject-123",
            "email": "alex@example.com",
            "name": "Alex Example",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "google-key-1"},
    )
    return token, {"keys": [public_jwk]}


def google_client(jwks: dict[str, object]) -> httpx.AsyncClient:
    def respond(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == GOOGLE_CERTIFICATES_URL
        return httpx.Response(200, json=jwks)

    return httpx.AsyncClient(transport=httpx.MockTransport(respond))


async def test_google_verifier_accepts_signed_token_for_exact_client() -> None:
    token, jwks = google_token(
        audience="tripper-client-id", issuer="https://accounts.google.com"
    )
    async with google_client(jwks) as client:
        identity = await GoogleIdentityVerifier("tripper-client-id", client).verify(
            token
        )

    assert identity.subject == "google-subject-123"
    assert identity.email == "alex@example.com"


@pytest.mark.parametrize(
    ("audience", "issuer"),
    [
        ("another-client-id", "https://accounts.google.com"),
        ("tripper-client-id", "https://attacker.example"),
    ],
)
async def test_google_verifier_rejects_wrong_audience_or_issuer(
    audience: str, issuer: str
) -> None:
    token, jwks = google_token(audience=audience, issuer=issuer)
    async with google_client(jwks) as client:
        verifier = GoogleIdentityVerifier("tripper-client-id", client)
        with pytest.raises(InvalidGoogleCredentialError):
            await verifier.verify(token)
