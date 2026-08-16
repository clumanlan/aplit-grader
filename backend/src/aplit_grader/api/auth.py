"""Verifies Cognito-issued access tokens and resolves the requesting teacher.

Access tokens (not ID tokens) are what AWS recommends presenting to a resource
server / API for authorization — the frontend's Cognito sign-in stores and
sends the AccessToken from InitiateAuth's AuthenticationResult.
"""

from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from aplit_grader.config import Settings, get_settings


class TeacherIdentity:
    """The authenticated teacher, resolved from a verified Cognito access token."""

    def __init__(self, sub: str, username: str | None) -> None:
        self.sub = sub
        self.username = username


_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _get_jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    # PyJWKClient fetches and caches Cognito's signing keys by kid; caching the
    # client itself (keyed on URL, effectively one per Settings instance) avoids
    # re-fetching the JWKS document on every request.
    return jwt.PyJWKClient(jwks_url)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_teacher(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> TeacherIdentity:
    if credentials is None:
        raise _unauthorized("Missing bearer token.")

    issuer = f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/{settings.cognito_user_pool_id}"
    jwks_url = f"{issuer}/.well-known/jwks.json"

    try:
        signing_key = _get_jwk_client(jwks_url).get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            # Cognito access tokens don't carry an `aud` claim (only ID tokens do) —
            # the app client is instead verified below via the `client_id` claim.
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise _unauthorized("Invalid or expired token.") from exc

    if claims.get("token_use") != "access":
        raise _unauthorized("Token is not a Cognito access token.")

    if claims.get("client_id") != settings.cognito_app_client_id:
        raise _unauthorized("Token was not issued for this application.")

    return TeacherIdentity(sub=claims["sub"], username=claims.get("username"))
