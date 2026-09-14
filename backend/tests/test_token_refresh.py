"""Regression tests for per-user access-token refresh.

Volvo rotates the refresh token on every use, so two concurrent refreshes for
one user would leave the loser holding a dead token and flip the account to
`needs_reconnect`. The glance and the widget both poll /v1/status, so this is a
normal-traffic race, not a theoretical one.
"""

import asyncio
import datetime as dt
import time

import pytest

from app import config, db, service
from app.volvo import Token, VolvoError


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("FERNET_KEY", "3z0Yb2Yq9nTjJv1nO0Xy8Kc5Ld7Mf4Pq6Rs8Tu0Wv2Y=")
    monkeypatch.setenv("DEVICE_TOKEN_PEPPER", "test-pepper")
    config.get_settings.cache_clear()
    db._engine = None
    db.init_db()
    with db.session_scope() as s:
        yield s
    db._engine = None
    config.get_settings.cache_clear()
    service._refresh_locks.clear()


def _make_user(session, *, expired: bool) -> db.User:
    offset = -60 if expired else 3600
    user = db.User(
        volvo_sub="sub-123",
        primary_vin="TESTVIN",
        refresh_token_enc=service.encrypt("refresh-1"),
        access_token="access-1",
        access_token_expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(seconds=offset),
    )
    session.add(user)
    session.commit()
    return user


class FakeClient:
    """Counts refreshes and yields control, so overlap is actually possible."""

    def __init__(self):
        self.calls = 0

    async def refresh(self, refresh_token: str) -> Token:
        self.calls += 1
        await asyncio.sleep(0.05)
        return Token(
            access_token=f"access-{self.calls + 1}",
            refresh_token=f"refresh-{self.calls + 1}",
            expires_at=time.time() + 300,
        )


async def test_valid_token_is_reused_without_refreshing(session, monkeypatch):
    user = _make_user(session, expired=False)
    fake = FakeClient()
    monkeypatch.setattr(service, "get_client", lambda: fake)

    assert await service.ensure_access_token(session, user) == "access-1"
    assert fake.calls == 0


async def test_expired_token_triggers_one_refresh(session, monkeypatch):
    user = _make_user(session, expired=True)
    fake = FakeClient()
    monkeypatch.setattr(service, "get_client", lambda: fake)

    assert await service.ensure_access_token(session, user) == "access-2"
    assert fake.calls == 1


async def test_concurrent_calls_refresh_only_once(session, monkeypatch):
    """The actual regression: two overlapping fetches must share one refresh."""
    user = _make_user(session, expired=True)
    fake = FakeClient()
    monkeypatch.setattr(service, "get_client", lambda: fake)

    results = await asyncio.gather(
        service.ensure_access_token(session, user),
        service.ensure_access_token(session, user),
        service.ensure_access_token(session, user),
    )

    assert fake.calls == 1, "refresh token was rotated more than once"
    assert set(results) == {"access-2"}
    assert user.needs_reconnect is False


async def test_failed_refresh_flags_needs_reconnect(session, monkeypatch):
    user = _make_user(session, expired=True)

    class DeadClient:
        async def refresh(self, refresh_token):
            raise VolvoError("invalid_grant", status=400, needs_reconnect=True)

    monkeypatch.setattr(service, "get_client", lambda: DeadClient())

    with pytest.raises(VolvoError):
        await service.ensure_access_token(session, user)
    assert user.needs_reconnect is True


async def test_already_flagged_user_short_circuits(session, monkeypatch):
    user = _make_user(session, expired=True)
    user.needs_reconnect = True
    session.commit()
    fake = FakeClient()
    monkeypatch.setattr(service, "get_client", lambda: fake)

    with pytest.raises(VolvoError) as err:
        await service.ensure_access_token(session, user)
    assert err.value.needs_reconnect
    assert fake.calls == 0


async def test_undecryptable_refresh_token_flags_needs_reconnect(session, monkeypatch):
    """A FERNET_KEY rotation (or a DB restored under an older key) leaves the
    stored refresh token undecryptable. Regression: this used to escape as a
    bare cryptography.fernet.InvalidToken, past every VolvoError handler, as
    an unhandled 500 instead of a clean needs_reconnect."""
    user = _make_user(session, expired=True)
    user.refresh_token_enc = "not a valid fernet token"
    session.commit()

    with pytest.raises(VolvoError) as err:
        await service.ensure_access_token(session, user)
    assert err.value.needs_reconnect
    assert user.needs_reconnect is True
