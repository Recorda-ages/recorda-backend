from app.core import security
from app.core.config import settings


def test_password_hash_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)

    password_hash = security.hash_password("secret")

    assert security.verify_password("secret", password_hash) is True
    assert security.verify_password("wrong", password_hash) is False


def test_verify_password_rejects_invalid_hash():
    assert security.verify_password("secret", "invalid") is False
    assert security.verify_password("secret", None) is False


def test_decode_access_token_rejects_invalid_and_expired_tokens(monkeypatch):
    assert security.decode_access_token("not-a-token") is None

    monkeypatch.setattr(settings, "access_token_expire_minutes", -1)
    expired_token = security.create_access_token(subject="1")

    assert security.decode_access_token(expired_token) is None
