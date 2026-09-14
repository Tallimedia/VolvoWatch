"""purge_expired() used to be a Python fetch-everything-then-loop, run on
every login. Rewritten as two DELETE...WHERE statements — this covers the
behavior actually stayed the same, including the OAuthFlow round-trip
through SQLite (DateTime columns come back naive even though `_utcnow()`
writes an aware value, which is why aware()/the naive-cutoff trick exist)."""

import datetime as dt

import pytest

from app import config, db


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    config.get_settings.cache_clear()
    db._engine = None
    db.init_db()
    with db.session_scope() as s:
        yield s
    db._engine = None
    config.get_settings.cache_clear()


def _flow(session, state: str, age_s: float) -> None:
    session.add(
        db.OAuthFlow(
            state=state,
            code_verifier="v",
            created_at=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=age_s),
        )
    )


def _pairing(session, code: str, *, age_s: float, consumed: bool) -> None:
    session.add(
        db.PairingCode(
            code=code,
            user_id=1,
            consumed=consumed,
            created_at=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=age_s),
        )
    )


def test_expired_flow_is_deleted_fresh_one_survives(session):
    _flow(session, "old", age_s=1000)
    _flow(session, "fresh", age_s=10)
    session.commit()

    db.purge_expired(session, flow_ttl_s=600, pairing_ttl_s=900)
    session.commit()

    remaining = {f.state for f in session.query(db.OAuthFlow).all()}
    assert remaining == {"fresh"}


def test_consumed_pairing_code_is_deleted_even_if_fresh(session):
    _pairing(session, "AAA111", age_s=5, consumed=True)
    _pairing(session, "BBB222", age_s=5, consumed=False)
    session.commit()

    db.purge_expired(session, flow_ttl_s=600, pairing_ttl_s=900)
    session.commit()

    remaining = {p.code for p in session.query(db.PairingCode).all()}
    assert remaining == {"BBB222"}


def test_expired_unconsumed_pairing_code_is_deleted(session):
    _pairing(session, "OLD999", age_s=2000, consumed=False)
    session.commit()

    db.purge_expired(session, flow_ttl_s=600, pairing_ttl_s=900)
    session.commit()

    assert session.query(db.PairingCode).count() == 0
