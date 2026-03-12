"""Тесты JWT авторизации."""
from jose import jwt

from app.core.auth import (
    ALGORITHM,
    create_access_token,
    hash_password,
    verify_password,
)
from app.core.config import settings


def test_hash_and_verify_password():
    password = "test_password_123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_create_access_token_contains_sub():
    token = create_access_token(operator_id=42)
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    assert payload["sub"] == "42"
    assert "exp" in payload


def test_token_with_wrong_secret_fails():
    token = create_access_token(operator_id=1)
    try:
        jwt.decode(token, "wrong-secret", algorithms=[ALGORITHM])
        assert False, "Should have raised"
    except Exception:
        pass
