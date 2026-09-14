"""SQLite persistence: users (Volvo tokens), OAuth flows, pairing codes, devices."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import String, create_engine, delete, or_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .config import get_settings


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    """One Volvo ID that has consented. Holds the (encrypted) refresh token."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    volvo_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    primary_vin: Mapped[str] = mapped_column(String(32), default="")
    scopes: Mapped[str] = mapped_column(default="")

    refresh_token_enc: Mapped[str] = mapped_column(default="")
    access_token: Mapped[str] = mapped_column(default="")
    access_token_expires_at: Mapped[dt.datetime] = mapped_column(default=_utcnow)
    needs_reconnect: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[dt.datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)


class OAuthFlow(Base):
    """Transient PKCE state for an in-flight authorization-code exchange."""

    __tablename__ = "oauth_flows"

    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    code_verifier: Mapped[str] = mapped_column()
    created_at: Mapped[dt.datetime] = mapped_column(default=_utcnow)


class PairingCode(Base):
    """Short code shown to the user after consent, typed into the watch once."""

    __tablename__ = "pairing_codes"

    code: Mapped[str] = mapped_column(String(12), primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    consumed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[dt.datetime] = mapped_column(default=_utcnow)


class Device(Base):
    """One watch paired to a user. Only the peppered token hash is stored."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(index=True)
    label: Mapped[str] = mapped_column(default="")
    created_at: Mapped[dt.datetime] = mapped_column(default=_utcnow)
    last_seen_at: Mapped[dt.datetime] = mapped_column(default=_utcnow)


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        if url.startswith("sqlite:///") and "./" in url:
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url, connect_args={"check_same_thread": False})
    return _engine


def init_db() -> None:
    Base.metadata.create_all(_get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    session = Session(_get_engine(), expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def purge_expired(session: Session, *, flow_ttl_s: int = 600, pairing_ttl_s: int = 900) -> None:
    """One DELETE per table instead of a Python scan-and-loop — this runs on
    every login, so a full table fetch per call doesn't scale with history."""
    # created_at is stored naive (SQLite round-trips DateTime without
    # timezone=True as naive) but was written from an aware UTC value — a
    # naive UTC cutoff compares correctly against it without needing aware().
    flow_cutoff = _utcnow().replace(tzinfo=None) - dt.timedelta(seconds=flow_ttl_s)
    pairing_cutoff = _utcnow().replace(tzinfo=None) - dt.timedelta(seconds=pairing_ttl_s)
    session.execute(delete(OAuthFlow).where(OAuthFlow.created_at < flow_cutoff))
    session.execute(
        delete(PairingCode).where(
            or_(PairingCode.consumed.is_(True), PairingCode.created_at < pairing_cutoff)
        )
    )


def aware(value: dt.datetime) -> dt.datetime:
    """SQLite round-trips DateTime columns as naive, even when the value
    written was timezone-aware — re-attach UTC so arithmetic against an
    aware `now` doesn't raise."""
    return value if value.tzinfo else value.replace(tzinfo=dt.UTC)
