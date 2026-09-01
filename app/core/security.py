"""Password and access-token helpers for authentication flows."""

import base64
import binascii
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings

_PASSWORD_SCHEME = "pbkdf2_sha256"
_TOKEN_ALGORITHM = "HS256"
_TOKEN_TYPE = "JWT"
_DEV_ACCESS_TOKEN_SECRET = secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = settings.password_hash_iterations
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "$".join(
        (
            _PASSWORD_SCHEME,
            str(iterations),
            _base64url_encode(salt),
            _base64url_encode(digest),
        )
    )


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        scheme, iterations_raw, salt_raw, digest_raw = password_hash.split("$", 3)
        if scheme != _PASSWORD_SCHEME:
            return False
        iterations = int(iterations_raw)
        salt = _base64url_decode(salt_raw)
        expected_digest = _base64url_decode(digest_raw)
    except (ValueError, binascii.Error):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(
    subject: str, additional_claims: dict[str, Any] | None = None
) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if additional_claims:
        payload.update(additional_claims)

    header = {"alg": _TOKEN_ALGORITHM, "typ": _TOKEN_TYPE}
    header_part = _base64url_encode(_json_bytes(header))
    payload_part = _base64url_encode(_json_bytes(payload))
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = _sign(signing_input)
    return f"{header_part}.{payload_part}.{signature}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        header_part, payload_part, signature = token.split(".")
    except ValueError:
        return None

    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    expected_signature = _sign(signing_input)
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        header = json.loads(_base64url_decode(header_part))
        payload = json.loads(_base64url_decode(payload_part))
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
        return None

    if header.get("alg") != _TOKEN_ALGORITHM or header.get("typ") != _TOKEN_TYPE:
        return None

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int):
        return None
    if datetime.now(UTC).timestamp() >= expires_at:
        return None

    return payload


def _sign(value: bytes) -> str:
    digest = hmac.new(_access_token_secret(), value, hashlib.sha256).digest()
    return _base64url_encode(digest)


def _access_token_secret() -> bytes:
    configured_secret = settings.access_token_secret_key
    if configured_secret:
        return configured_secret.encode("utf-8")
    if settings.environment == "production":
        raise RuntimeError("ACCESS_TOKEN_SECRET_KEY must be configured")
    return _DEV_ACCESS_TOKEN_SECRET.encode("utf-8")


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
