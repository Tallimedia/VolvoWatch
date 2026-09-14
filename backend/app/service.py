"""Business logic tying the DB, crypto and Volvo client together."""

from __future__ import annotations

import asyncio
import datetime as dt
import time
from typing import Any

from cryptography.fernet import InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .crypto import decrypt, encrypt, hash_device_token
from .db import Device, User, aware
from .schemas import VehicleStatus
from .volvo import Token, VolvoClient, VolvoError

# Keyed by user id, not VIN — `User.primary_vin` defaults to "" until a
# vehicle is linked, so two different accounts with no VIN yet (or, less
# plausibly, a genuine VIN collision) would otherwise share one cache slot
# and one account could be served from another's cached status.
_status_cache: dict[int, tuple[float, VehicleStatus]] = {}

# Volvo rotates the refresh token on every use, so two concurrent refreshes for
# the same user would invalidate each other and bounce them to "reconnect".
# The glance and the widget both fetch status, so this happens in normal use.
#
# Also an unbounded module global, deliberately left that way: a Lock is a
# few dozen bytes, and unlike _status_cache there's no safe way to evict one
# — removing an entry a concurrent request is still `async with`-holding a
# reference to would split one user's refreshes across two different Lock
# objects, defeating the reason this dict exists. Not worth the risk for a
# self-hosted app with a handful of users, ever.
_refresh_locks: dict[int, asyncio.Lock] = {}


_client: VolvoClient | None = None


def get_client() -> VolvoClient:
    """A cached singleton, not a fresh instance per call — VolvoClient now
    holds a persistent httpx connection pool (see volvo.py), so recreating
    it every call would throw that pool away immediately."""
    global _client
    s = get_settings()
    s.require_volvo_credentials()  # still checked every call, fail fast
    if _client is None:
        _client = VolvoClient(
            client_id=s.volvo_client_id,
            client_secret=s.volvo_client_secret,
            vcc_api_key=s.volvo_vcc_api_key,
            redirect_uri=s.volvo_redirect_uri,
        )
    return _client


def store_token(session: Session, user: User, token: Token) -> None:
    user.refresh_token_enc = encrypt(token.refresh_token)
    user.access_token = token.access_token
    user.access_token_expires_at = dt.datetime.fromtimestamp(token.expires_at, dt.UTC)
    user.needs_reconnect = False
    if token.scope:
        user.scopes = token.scope
    session.add(user)


def _usable_access_token(user: User) -> str | None:
    """The stored access token, if it's still good for at least 30 more seconds."""
    if not user.access_token:
        return None
    expires_at = aware(user.access_token_expires_at)
    return user.access_token if expires_at.timestamp() > time.time() + 30 else None


def _refresh_lock(user_id: int) -> asyncio.Lock:
    lock = _refresh_locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _refresh_locks[user_id] = lock
    return lock


async def ensure_access_token(session: Session, user: User) -> str:
    """Return a currently-valid Volvo access token, refreshing if needed.

    Refreshes are serialised per user: the refresh token is single-use, so two
    concurrent refreshes would leave one of them holding a dead token.
    """
    if user.needs_reconnect:
        raise VolvoError("user must re-consent", needs_reconnect=True)

    token = _usable_access_token(user)
    if token is not None:
        return token

    async with _refresh_lock(user.id):
        # Another request may have refreshed while we waited — re-read the row.
        session.refresh(user)
        if user.needs_reconnect:
            raise VolvoError("user must re-consent", needs_reconnect=True)
        token = _usable_access_token(user)
        if token is not None:
            return token

        try:
            new_token = await get_client().refresh(decrypt(user.refresh_token_enc))
        except InvalidToken:
            # FERNET_KEY rotated (or the DB was restored from a backup taken
            # under an older key) — the stored refresh token can't be read at
            # all. Same recovery as a genuine Volvo-side refresh failure:
            # flag for re-consent rather than letting this reach the client
            # as a bare 500.
            user.needs_reconnect = True
            session.add(user)
            raise VolvoError(
                "stored refresh token could not be decrypted", needs_reconnect=True
            ) from None
        except VolvoError as exc:
            if exc.needs_reconnect:
                user.needs_reconnect = True
                session.add(user)
            raise
        store_token(session, user, new_token)
        session.commit()  # publish the rotated refresh token before releasing the lock
        return new_token.access_token


def resolve_device(session: Session, bearer: str) -> tuple[Device, User]:
    device = session.scalar(
        select(Device).where(Device.token_hash == hash_device_token(bearer))
    )
    if device is None:
        raise LookupError("unknown device token")
    user = session.get(User, device.user_id)
    if user is None:
        raise LookupError("device has no user")
    device.last_seen_at = dt.datetime.now(dt.UTC)
    session.add(device)
    return device, user


def _num(field: dict[str, Any] | None) -> float | None:
    if not isinstance(field, dict):
        return None
    value = field.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _val(field: dict[str, Any] | None) -> Any:
    return field.get("value") if isinstance(field, dict) else None


async def build_status(session: Session, user: User) -> VehicleStatus:
    now = time.time()
    cached = _status_cache.get(user.id)
    if cached and now - cached[0] < get_settings().status_cache_ttl:
        return cached[1]

    access_token = await ensure_access_token(session, user)
    client = get_client()
    vin = user.primary_vin

    async def safe(coro):
        try:
            return await coro
        except VolvoError as exc:
            if exc.needs_reconnect:
                raise
            return {}

    # One connection-pooled client (see volvo.py) makes these safe to fire
    # concurrently instead of one-at-a-time — was ~9 sequential round trips
    # per /v1/status fetch.
    keys = (
        "fuel", "energy", "statistics", "odometer", "doors",
        "windows", "diagnostics", "tyres", "command_accessibility",
    )
    calls = (
        client.fuel(access_token, vin),
        client.energy_state(access_token, vin),
        client.statistics(access_token, vin),
        client.odometer(access_token, vin),
        client.doors(access_token, vin),
        client.windows(access_token, vin),
        client.diagnostics(access_token, vin),
        client.tyres(access_token, vin),
        client.command_accessibility(access_token, vin),
    )
    results = await asyncio.gather(*(safe(c) for c in calls))
    payloads = dict(zip(keys, results))
    status = assemble_status(vin, payloads, needs_reconnect=user.needs_reconnect)
    _status_cache[user.id] = (now, status)
    _prune_status_cache(now)
    return status


# _status_cache is an unbounded module global — a dead/removed user's entry
# would otherwise sit there forever. An active user refreshes their own
# entry roughly every status_cache_ttl (default 60s), so anything still
# around after an hour is abandoned, not just between polls.
_STATUS_CACHE_MAX_AGE_S = 3600


def _prune_status_cache(now: float) -> None:
    stale = [uid for uid, (ts, _) in _status_cache.items() if now - ts > _STATUS_CACHE_MAX_AGE_S]
    for uid in stale:
        _status_cache.pop(uid, None)


def assemble_status(
    vin: str, payloads: dict[str, dict[str, Any]], *, needs_reconnect: bool = False
) -> VehicleStatus:
    """Pure mapping from raw Volvo payloads to the compact watch shape.

    Field names/shapes verified against a 2024 XC60 PHEV on 2026-09-03; see
    spike/FINDINGS.md.
    """
    def unwrap(key: str) -> dict[str, Any]:
        """Connected-Vehicle wraps payloads in {"data": {...}}; energy/v2 does not."""
        payload = payloads.get(key)
        if not isinstance(payload, dict):
            return {}
        inner = payload.get("data", payload)
        return inner if isinstance(inner, dict) else {}

    fuel_d = unwrap("fuel")
    energy_d = unwrap("energy")
    stats_d = unwrap("statistics")
    odo_d = unwrap("odometer")
    doors_d = unwrap("doors")
    windows_d = unwrap("windows")
    diag_d = unwrap("diagnostics")
    tyres_d = unwrap("tyres")
    access_d = unwrap("command_accessibility")

    fuel_range = _num(stats_d.get("distanceToEmptyTank"))
    batt_range = _num(energy_d.get("electricRange")) or _num(stats_d.get("distanceToEmptyBattery"))
    combined = None
    if fuel_range is not None or batt_range is not None:
        combined = round((fuel_range or 0) + (batt_range or 0))

    open_states = {"OPEN", "AJAR"}
    state_keys = ("frontLeftDoor", "frontRightDoor", "rearLeftDoor", "rearRightDoor",
                  "hood", "tailgate", "tankLid")
    door_vals = [str(_val(doors_d.get(k))).upper() for k in state_keys if k in doors_d]
    window_vals = [str(_val(v)).upper() for v in windows_d.values()]
    doors_closed = not any(s in open_states for s in door_vals) if door_vals else None
    windows_closed = not any(s in open_states for s in window_vals) if window_vals else None
    all_closed: bool | None = None
    if door_vals or window_vals:
        all_closed = not any(s in open_states for s in door_vals + window_vals)

    locked_raw = _val(doors_d.get("centralLock"))
    locked = {"LOCKED": True, "UNLOCKED": False}.get(str(locked_raw).upper())

    charging_raw = _val(energy_d.get("chargingStatus"))
    charging_type = _val(energy_d.get("chargingType"))
    charger_conn = str(_val(energy_d.get("chargerConnectionStatus")) or "").upper()
    # Volvo's connection enum isn't just CONNECTED/DISCONNECTED — e.g. a
    # charging-specific variant would fail an exact "CONNECTED" match and
    # wrongly report unplugged while mid-charge. Only DISCONNECTED means not
    # plugged in; anything else known is plugged in.
    plugged_in = (charger_conn != "DISCONNECTED") if charger_conn else None

    fuel_litres = _num(fuel_d.get("fuelAmount"))
    tank = get_settings().fuel_tank_litres
    # `is not None` — an empty tank is a legitimate 0.0, not "unknown"; the
    # old `if fuel_litres and tank` collapsed that to null (same bug already
    # fixed once for time_to_full_min).
    fuel_pct = (
        round(min(fuel_litres / tank * 100, 100), 1)
        if fuel_litres is not None and tank
        else None
    )

    ttf = _num(energy_d.get("estimatedChargingTimeToTargetBatteryChargeLevel"))
    service_months = _num(diag_d.get("timeToService"))
    service_km = _num(diag_d.get("distanceToService"))
    service_warning = str(_val(diag_d.get("serviceWarning")) or "").upper()
    service_due = None
    if diag_d:
        service_due = service_warning not in ("", "NO_WARNING") or service_km == 0

    washer_raw = str(_val(diag_d.get("washerFluidLevelWarning")) or "").upper()
    washer_fluid_low = None if not diag_d else washer_raw not in ("", "NO_WARNING")

    # Per-corner tyre status. "UNSPECIFIED" = the car isn't reporting → None.
    tyre_ok = {"", "NO_WARNING", "NORMAL", "OK"}
    tyre_vals = [str(_val(v) or "").upper() for v in tyres_d.values()]
    tyre_known = [v for v in tyre_vals if v and v != "UNSPECIFIED"]
    tyre_warning = None if not tyre_known else any(v not in tyre_ok for v in tyre_known)

    avg_fuel = _num(stats_d.get("averageFuelConsumption"))
    trip_km = _num(stats_d.get("tripMeterManual"))
    trip_auto_km = _num(stats_d.get("tripMeterAutomatic"))

    charging_power = _num(energy_d.get("chargingPower"))

    reachable, reason = _reachability(access_d)

    status = VehicleStatus(
        vin=vin,
        fuel_litres=fuel_litres,
        fuel_pct=fuel_pct,
        battery_pct=_num(energy_d.get("batteryChargeLevel")),
        fuel_range_km=fuel_range,
        battery_range_km=batt_range,
        range_km=combined,
        charging=str(charging_raw).lower() if charging_raw else None,
        charging_type=str(charging_type).lower() if charging_type else None,
        charging_power_w=charging_power,
        time_to_full_min=int(ttf) if ttf is not None else None,
        plugged_in=plugged_in,
        locked=locked,
        all_closed=all_closed,
        doors_closed=doors_closed,
        windows_closed=windows_closed,
        odometer_km=_num(odo_d.get("odometer")),
        avg_fuel_l_100=avg_fuel,
        trip_km=trip_km,
        trip_auto_km=trip_auto_km,
        service_due=service_due,
        service_in_km=service_km,
        service_in_months=int(service_months) if service_months is not None else None,
        washer_fluid_low=washer_fluid_low,
        tyre_warning=tyre_warning,
        car_reachable=reachable,
        unreachable_reason=reason,
        updated_at=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        stale=_is_stale(fuel_d, energy_d, stats_d),
        needs_reconnect=needs_reconnect,
    )
    return status


def _reachability(access_d: dict[str, Any]) -> tuple[bool | None, str | None]:
    field = access_d.get("availabilityStatus")
    if not isinstance(field, dict):
        return None, None
    value = str(field.get("value") or "").upper()
    if not value:
        return None, None
    reachable = value == "AVAILABLE"
    return reachable, (None if reachable else field.get("unavailableReason"))


def _is_stale(*fields: dict[str, Any]) -> bool:
    newest: dt.datetime | None = None
    for field in fields:
        for entry in field.values() if isinstance(field, dict) else []:
            if not isinstance(entry, dict):
                continue
            ts = entry.get("timestamp") or entry.get("updatedAt")
            if not isinstance(ts, str):
                continue
            try:
                parsed = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            parsed = aware(parsed)  # never mix naive and aware
            newest = parsed if newest is None or parsed > newest else newest
    if newest is None:
        return False
    return (dt.datetime.now(dt.UTC) - newest).total_seconds() > 3600


def invalidate_status_cache(user_id: int) -> None:
    _status_cache.pop(user_id, None)
