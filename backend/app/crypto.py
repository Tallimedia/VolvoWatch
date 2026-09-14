"""Symmetric encryption for refresh tokens at rest, and device-token hashing."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet

from .config import get_settings


def _fernet() -> Fernet:
    key = get_settings().fernet_key
    if not key:
        raise RuntimeError("FERNET_KEY is not set (run `python -m app.cli gen-keys`)")
    return Fernet(key.encode())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def new_device_token() -> str:
    """A long, opaque bearer token handed to one watch."""
    return secrets.token_urlsafe(32)


def hash_device_token(token: str) -> str:
    """Peppered SHA-256 — only the hash is stored, so a DB leak can't be replayed."""
    pepper = get_settings().device_token_pepper
    if not pepper:
        raise RuntimeError("DEVICE_TOKEN_PEPPER is not set (run `python -m app.cli gen-keys`)")
    return hmac.new(pepper.encode(), token.encode(), hashlib.sha256).hexdigest()


def new_pairing_code() -> str:
    """6 digits — easy to read out, and easy to enter on a watch digit-wheel.

    Single-use and 15-min TTL; /v1/pair needs rate limiting before this goes
    public (~1e6 space).
    """
    return "".join(secrets.choice("0123456789") for _ in range(6))
