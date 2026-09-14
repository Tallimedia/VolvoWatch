"""Regression test: a `needs_reconnect` flip during /v1/command must survive.

`ensure_access_token()` sets `user.needs_reconnect = True` on the in-memory
row when Volvo's refresh fails, but `command()` used to just `raise` straight
through `session_scope()`'s `with` block — whose except-clause rolls back on
any exception. The flag was set, then silently discarded, so every future
command on that device kept retrying the same doomed refresh instead of
surfacing "reconnect Volvo" to the watch. Fixed by committing explicitly in
watch_routes.py's command() before re-raising.
"""

import datetime as dt

import pytest
from fastapi import HTTPException

from app import config, db, service
from app.crypto import hash_device_token, new_device_token
from app.volvo import VolvoError
from app.watch_routes import command


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("FERNET_KEY", "3z0Yb2Yq9nTjJv1nO0Xy8Kc5Ld7Mf4Pq6Rs8Tu0Wv2Y=")
    monkeypatch.setenv("DEVICE_TOKEN_PEPPER", "test-pepper")
    monkeypatch.setenv("VOLVO_SCOPES", "openid conve:climatization_start_stop")
    config.get_settings.cache_clear()
    db._engine = None
    db.init_db()
    yield
    db._engine = None
    config.get_settings.cache_clear()
    service._refresh_locks.clear()


async def test_needs_reconnect_survives_a_failed_command(env, monkeypatch):
    token = new_device_token()
    with db.session_scope() as session:
        user = db.User(
            volvo_sub="sub-123",
            primary_vin="TESTVIN",
            refresh_token_enc=service.encrypt("refresh-1"),
            access_token="",
            access_token_expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=60),
        )
        session.add(user)
        session.flush()
        session.add(db.Device(token_hash=hash_device_token(token), user_id=user.id))

    class DeadClient:
        async def refresh(self, refresh_token):
            raise VolvoError("invalid_grant", status=400, needs_reconnect=True)

    monkeypatch.setattr(service, "get_client", lambda: DeadClient())

    with pytest.raises(HTTPException) as err:
        await command("climate-start", authorization=f"Bearer {token}")
    assert err.value.status_code == 502

    with db.session_scope() as session:
        refreshed = session.scalars(
            db.select(db.User).where(db.User.volvo_sub == "sub-123")
        ).one()
        assert refreshed.needs_reconnect is True
