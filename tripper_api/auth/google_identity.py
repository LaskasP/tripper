from typing import cast

import httpx
import jwt
from jwt import PyJWKSet

from tripper_api.auth.auth_errors import InvalidGoogleCredentialError
from tripper_api.auth.auth_identity import GoogleIdentity
from tripper_api.core.constants import GOOGLE_CERTIFICATES_URL, TRUSTED_ISSUERS


class GoogleIdentityVerifier:
    def __init__(self, client_id: str, client: httpx.AsyncClient) -> None:
        self._client_id = client_id
        self._client = client

    async def verify(self, credential: str) -> GoogleIdentity:
        try:
            header = jwt.get_unverified_header(credential)
            response = await self._client.get(GOOGLE_CERTIFICATES_URL)
            response.raise_for_status()
            key_set = PyJWKSet.from_dict(response.json())
            key = next(key.key for key in key_set.keys if key.key_id == header["kid"])
            claims = jwt.decode(
                credential,
                key,
                algorithms=["RS256"],
                audience=self._client_id,
                issuer=list(TRUSTED_ISSUERS),
                options={"require": ["exp", "iat", "iss", "aud", "sub", "email"]},
            )
            return GoogleIdentity(
                issuer=cast(str, claims["iss"]),
                subject=cast(str, claims["sub"]),
                email=cast(str, claims["email"]),
                display_name=cast(str, claims.get("name") or claims["email"]),
            )
        except (
            httpx.HTTPError,
            jwt.PyJWTError,
            KeyError,
            StopIteration,
            TypeError,
        ) as exc:
            raise InvalidGoogleCredentialError from exc
