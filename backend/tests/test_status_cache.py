"""Regression: the status cache used to be keyed by VIN alone.

`User.primary_vin` defaults to "" until a vehicle is linked, so two different
accounts with no VIN yet (both keyed under "") would share one cache slot —
the second account's /v1/status could be served from the first account's
cached data. Fixed by keying the cache on `User.id` instead, which is always
unique regardless of VIN state.
"""

import datetime as dt

import pytest

from app import config, db, service


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
    service._status_cache.clear()


def _make_user(session, sub: str, *, vin: str = "") -> db.User:
    user = db.User(
        volvo_sub=sub,
        primary_vin=vin,
        refresh_token_enc=service.encrypt("refresh-1"),
        access_token="access-1",
        access_token_expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(seconds=3600),
    )
    session.add(user)
    session.commit()
    return user


class CountingClient:
    """Stands in for VolvoClient — counts real fetches so cache hits/misses
    are observable."""

    def __init__(self):
        self.calls = 0

    async def fuel(self, access_token, vin):
        self.calls += 1
        return {}

    async def energy_state(self, access_token, vin):
        return {}

    async def statistics(self, access_token, vin):
        return {}

    async def odometer(self, access_token, vin):
        return {}

    async def doors(self, access_token, vin):
        return {}

    async def windows(self, access_token, vin):
        return {}

    async def diagnostics(self, access_token, vin):
        return {}

    async def tyres(self, access_token, vin):
        return {}

    async def command_accessibility(self, access_token, vin):
        return {}


async def test_two_users_with_the_same_empty_vin_do_not_share_a_cache_slot(session, monkeypatch):
    user_a = _make_user(session, "sub-a")
    user_b = _make_user(session, "sub-b")
    assert user_a.primary_vin == user_b.primary_vin == ""  # the collision-prone case

    fake = CountingClient()
    monkeypatch.setattr(service, "get_client", lambda: fake)

    await service.build_status(session, user_a)
    await service.build_status(session, user_b)

    assert fake.calls == 2, "second user was served the first user's cached status"


async def test_same_user_second_call_is_served_from_cache(session, monkeypatch):
    user = _make_user(session, "sub-a")
    fake = CountingClient()
    monkeypatch.setattr(service, "get_client", lambda: fake)

    await service.build_status(session, user)
    await service.build_status(session, user)

    assert fake.calls == 1, "cache should still work within a single user"


async def test_invalidate_status_cache_uses_user_id():
    service._status_cache[42] = (0.0, "placeholder")
    service.invalidate_status_cache(42)
    assert 42 not in service._status_cache


def test_prune_status_cache_drops_only_abandoned_entries():
    """Regression: _status_cache is an unbounded module global — a
    dead/removed user's entry would otherwise sit there forever."""
    now = 10_000.0
    service._status_cache[1] = (now - 10, "recent")  # well within TTL
    service._status_cache[2] = (now - service._STATUS_CACHE_MAX_AGE_S - 1, "abandoned")

    service._prune_status_cache(now)

    assert 1 in service._status_cache
    assert 2 not in service._status_cache
