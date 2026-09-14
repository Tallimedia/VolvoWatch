"""Watch-facing API. Auth: `Authorization: Bearer <device_token>` (from pairing)."""

from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select

from . import ratelimit
from .config import get_settings
from .crypto import hash_device_token, new_device_token
from .db import Device, PairingCode, aware, session_scope
from .schemas import CommandResult, PairRequest, PairResponse, VehicleStatus
from .service import (
    build_status,
    ensure_access_token,
    get_client,
    invalidate_status_cache,
    resolve_device,
)
from .volvo import COMMANDS, VolvoError, has_command_scope

router = APIRouter(prefix="/v1", tags=["watch"])

_log = logging.getLogger(__name__)
_PAIRING_TTL_S = 15 * 60

# 6-digit code = 1e6 space; this caps a single IP to a small handful of
# tries per window, which is nowhere near enough to brute-force one within
# its 15-minute validity. See ratelimit.py for the (single-process) caveat.
_PAIR_MAX_ATTEMPTS = 5
_PAIR_WINDOW_S = 300.0


def _client_ip(request: Request) -> str:
    # Behind Cloudflare's proxy — request.client.host would just be the
    # tunnel/Traefik hop, not the real client.
    return request.headers.get("cf-connecting-ip") or (
        request.client.host if request.client else "unknown"
    )


def _upstream_error(exc: VolvoError, where: str) -> HTTPException:
    """Log the detail; hand the client a generic message.

    Volvo error strings can carry chunks of upstream response bodies, which have
    no business reaching a watch.
    """
    _log.warning("volvo error during %s: %s", where, exc)
    if exc.needs_reconnect:
        return HTTPException(502, "reconnect Volvo — open the connect page")
    if exc.status == 429:
        return HTTPException(429, "Volvo is rate limiting — try again shortly")
    return HTTPException(502, "Volvo request failed")


@router.post("/pair", response_model=PairResponse)
async def pair(body: PairRequest, request: Request) -> PairResponse:
    if not ratelimit.allow(
        f"pair:{_client_ip(request)}", max_attempts=_PAIR_MAX_ATTEMPTS, window_s=_PAIR_WINDOW_S
    ):
        raise HTTPException(429, "too many pairing attempts — try again in a few minutes")
    code = "".join(ch for ch in body.code.strip().upper() if ch.isalnum())
    with session_scope() as session:
        pc = session.get(PairingCode, code)
        if pc is None or pc.consumed:
            raise HTTPException(404, "invalid or already-used pairing code")
        age = (dt.datetime.now(dt.UTC) - aware(pc.created_at)).total_seconds()
        if age > _PAIRING_TTL_S:
            raise HTTPException(410, "pairing code expired — reconnect at /link")

        token = new_device_token()
        session.add(
            Device(
                token_hash=hash_device_token(token),
                user_id=pc.user_id,
                label=body.label[:64],
            )
        )
        pc.consumed = True
        session.add(pc)

        from .db import User  # local import to avoid cycle at module load

        user = session.get(User, pc.user_id)
        vin = user.primary_vin if user else ""
    return PairResponse(device_token=token, vin=vin)


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    return authorization.split(" ", 1)[1].strip()


@router.get("/status", response_model=VehicleStatus)
async def status(authorization: str | None = Header(default=None)) -> VehicleStatus:
    with session_scope() as session:
        try:
            _, user = resolve_device(session, _bearer(authorization))
        except LookupError:
            raise HTTPException(401, "unknown device — re-pair from /link") from None
        try:
            return await build_status(session, user)
        except VolvoError as exc:
            if exc.needs_reconnect:
                return VehicleStatus(
                    vin=user.primary_vin,
                    updated_at=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                    needs_reconnect=True,
                )
            raise _upstream_error(exc, "status") from exc


_COMMAND_OK = {"COMPLETED", "DELIVERED", "WAITING", "RUNNING"}


@router.post("/command/{name}", response_model=CommandResult)
async def command(name: str, authorization: str | None = Header(default=None)) -> CommandResult:
    if name not in COMMANDS:
        raise HTTPException(404, f"unknown command; known: {sorted(COMMANDS)}")
    with session_scope() as session:
        try:
            _, user = resolve_device(session, _bearer(authorization))
        except LookupError:
            raise HTTPException(401, "unknown device — re-pair from /link") from None
        if not has_command_scope(get_settings().volvo_scopes, name):
            raise HTTPException(
                403,
                f"'{name}' needs a Volvo scope this account hasn't granted — "
                "reconnect at /link",
            )
        try:
            access_token = await ensure_access_token(session, user)
            result = await get_client().send_command(access_token, user.primary_vin, name)
        except VolvoError as exc:
            # A timeout is not a failure we can assert — Volvo may well have
            # delivered it. Report it as an inconclusive result, not an error,
            # so the watch doesn't claim the backend is unreachable.
            if exc.timed_out:
                _log.warning("timeout sending %s: %s", name, exc)
                invalidate_status_cache(user.id)
                return CommandResult(
                    command=name,
                    invoke_status="TIMEOUT",
                    ok=False,
                    message="Sent, but the car did not confirm in time",
                )
            if exc.needs_reconnect:
                # ensure_access_token() already set user.needs_reconnect on
                # this in-memory row — commit it explicitly here, since
                # raising past session_scope()'s `with` block would
                # otherwise roll it back, leaving every future command on
                # this device silently repeating the same doomed refresh.
                session.commit()
            raise _upstream_error(exc, f"command {name}") from exc
        invalidate_status_cache(user.id)

    data = result.get("data", result)
    if not isinstance(data, dict):
        data = {}
    invoke_status = str(data.get("invokeStatus") or data.get("status") or "UNKNOWN").upper()
    return CommandResult(
        command=name,
        invoke_status=invoke_status,
        ok=invoke_status in _COMMAND_OK,
        message=(data.get("message") or None),
    )


@router.get("/devices")
async def list_devices(authorization: str | None = Header(default=None)) -> dict:
    with session_scope() as session:
        try:
            _, user = resolve_device(session, _bearer(authorization))
        except LookupError:
            raise HTTPException(401, "unknown device") from None
        devices = session.scalars(select(Device).where(Device.user_id == user.id)).all()
        return {
            "vin": user.primary_vin,
            "devices": [
                {"label": d.label, "created_at": d.created_at.isoformat(), "id": d.id}
                for d in devices
            ],
        }
