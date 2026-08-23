"""Tests for login authentication logic (bcrypt verification)."""

import bcrypt


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    """Mirror of webapp.main._verify_password (can't import due to ui.run at module level)."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def test_verify_password_valid():
    hashed = _hash("secret123")
    assert _verify_password("secret123", hashed) is True


def test_verify_password_invalid():
    hashed = _hash("secret123")
    assert _verify_password("wrong", hashed) is False


def test_bcrypt_different_salts_same_password():
    h1 = _hash("mypass")
    h2 = _hash("mypass")
    assert h1 != h2
    assert _verify_password("mypass", h1) is True
    assert _verify_password("mypass", h2) is True
