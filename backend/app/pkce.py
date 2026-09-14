"""PKCE (RFC 7636) helpers for the OAuth authorization-code flow."""

from __future__ import annotations

import base64
import hashlib
import secrets


def generate_code_verifier(length: int = 96) -> str:
    if not 43 <= length <= 128:
        raise ValueError("code_verifier length must be 43..128")
    return secrets.token_urlsafe(length)[:length]


def code_challenge_s256(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def generate_state() -> str:
    return secrets.token_urlsafe(24)
