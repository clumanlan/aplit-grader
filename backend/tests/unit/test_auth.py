import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from aplit_grader.api.auth import get_current_teacher
from aplit_grader.config import Settings


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture
def settings():
    return Settings(
        cognito_region="us-east-2",
        cognito_user_pool_id="us-east-2_hZY5RNs81",
        cognito_app_client_id="7amuvrc9l1sn727kqp6paraoqk",
    )


def _issuer(settings: Settings) -> str:
    return f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/{settings.cognito_user_pool_id}"


def _make_token(private_key, settings: Settings, **claim_overrides) -> str:
    now = int(time.time())
    claims = {
        "sub": "abc-123",
        "token_use": "access",
        "client_id": settings.cognito_app_client_id,
        "username": "teacher@example.com",
        "iss": _issuer(settings),
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(claim_overrides)
    return jwt.encode(claims, private_key, algorithm="RS256")


def _patch_jwk_client(monkeypatch, public_key) -> None:
    fake_signing_key = SimpleNamespace(key=public_key)

    class FakeJWKClient:
        def get_signing_key_from_jwt(self, token):
            return fake_signing_key

    monkeypatch.setattr("aplit_grader.api.auth._get_jwk_client", lambda jwks_url: FakeJWKClient())


async def test_accepts_a_valid_access_token(monkeypatch, rsa_keypair, settings):
    private_key, public_key = rsa_keypair
    _patch_jwk_client(monkeypatch, public_key)
    token = _make_token(private_key, settings)

    teacher = await get_current_teacher(
        credentials=SimpleNamespace(credentials=token), settings=settings
    )

    assert teacher.sub == "abc-123"
    assert teacher.username == "teacher@example.com"


async def test_rejects_missing_credentials(settings):
    with pytest.raises(HTTPException) as exc_info:
        await get_current_teacher(credentials=None, settings=settings)

    assert exc_info.value.status_code == 401


async def test_rejects_an_id_token(monkeypatch, rsa_keypair, settings):
    private_key, public_key = rsa_keypair
    _patch_jwk_client(monkeypatch, public_key)
    token = _make_token(private_key, settings, token_use="id")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_teacher(
            credentials=SimpleNamespace(credentials=token), settings=settings
        )

    assert exc_info.value.status_code == 401


async def test_rejects_a_token_issued_for_a_different_app_client(monkeypatch, rsa_keypair, settings):
    private_key, public_key = rsa_keypair
    _patch_jwk_client(monkeypatch, public_key)
    token = _make_token(private_key, settings, client_id="some-other-client-id")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_teacher(
            credentials=SimpleNamespace(credentials=token), settings=settings
        )

    assert exc_info.value.status_code == 401


async def test_rejects_an_expired_token(monkeypatch, rsa_keypair, settings):
    private_key, public_key = rsa_keypair
    _patch_jwk_client(monkeypatch, public_key)
    now = int(time.time())
    token = _make_token(private_key, settings, iat=now - 7200, exp=now - 3600)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_teacher(
            credentials=SimpleNamespace(credentials=token), settings=settings
        )

    assert exc_info.value.status_code == 401


async def test_rejects_a_token_signed_by_an_untrusted_key(monkeypatch, rsa_keypair, settings):
    private_key, _public_key = rsa_keypair
    # Verify against an unrelated key's public half, simulating a forged signature.
    imposter_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _patch_jwk_client(monkeypatch, imposter_private_key.public_key())
    token = _make_token(private_key, settings)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_teacher(
            credentials=SimpleNamespace(credentials=token), settings=settings
        )

    assert exc_info.value.status_code == 401
