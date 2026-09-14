"""User-facing OAuth: /link landing page, Volvo consent redirect, callback."""

from __future__ import annotations

import base64
import binascii
import html
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from .config import get_settings
from .crypto import new_pairing_code
from .db import OAuthFlow, PairingCode, User, purge_expired, session_scope
from .pkce import code_challenge_s256, generate_code_verifier, generate_state
from .service import get_client, store_token
from .volvo import VolvoError
from .webshell import page as _page

router = APIRouter(tags=["auth"])

_log = logging.getLogger(__name__)


@router.get("/", response_class=HTMLResponse)
@router.get("/link", response_class=HTMLResponse)
async def link_landing() -> str:
    return _page(
        "VolvoWatch — connect",
        '<p class="text-muted">This page pairs a <b>Garmin watch</b> running the '
        "VolvoWatch app with your Volvo — it's not something you need unless "
        "you already have that app open on your wrist or phone.</p>"
        "<h1>Connect your Volvo</h1>"
        "<p>Sign in with your Volvo ID to let VolvoWatch read your car's status "
        "and start climatisation from your watch.</p>"
        '<p><a class="btn btn-primary" style="text-transform: uppercase; '
        'letter-spacing: 0.06em" href="/auth/login">Sign in with Volvo</a></p>'
        '<p class="text-muted">You sign in on Volvo\'s own site. This service never sees '
        "your password. Afterwards you'll get a short pairing code to enter in "
        "the watch app.</p>"
        '<p class="text-muted">Provided as-is with no SLA. Currently free; if that ever '
        "changes you'll be asked to accept before anything is charged — see the "
        '<a href="/terms">Terms of Service</a>.</p>',
    )


@router.get("/auth/login")
async def auth_login() -> RedirectResponse:
    s = get_settings()
    s.require_volvo_credentials()
    state = generate_state()
    verifier = generate_code_verifier()
    with session_scope() as session:
        purge_expired(session)
        session.add(OAuthFlow(state=state, code_verifier=verifier))
    url = get_client().authorize_url(
        scopes=s.scope_list, state=state, code_challenge=code_challenge_s256(verifier)
    )
    return RedirectResponse(url, status_code=302)


@router.get("/auth/callback", response_class=HTMLResponse)
async def auth_callback(request: Request, code: str = "", state: str = "", error: str = "") -> str:
    if error:
        _log.info("callback returned error=%r", error)
        raise HTTPException(400, "Volvo declined the sign-in — start again at /link")
    if not code or not state:
        raise HTTPException(400, "missing code/state")

    with session_scope() as session:
        flow = session.get(OAuthFlow, state)
        if flow is None:
            raise HTTPException(400, "unknown or expired login attempt — start again at /link")
        verifier = flow.code_verifier
        session.delete(flow)

    try:
        token = await get_client().exchange_code(code=code, code_verifier=verifier)
        access_token = token.access_token
        vins = await get_client().list_vehicles(access_token)
    except VolvoError as exc:
        _log.warning("callback token/vehicle lookup failed: %s", exc)
        raise HTTPException(502, "Volvo sign-in failed — please try again") from exc

    # No VIN fallback here on purpose: a VIN identifies a *car*, not a Volvo
    # account, and two different people who both have access to the same
    # car (e.g. household members) would collide onto one `User` row —
    # each sign-in silently overwriting the other's stored tokens.
    sub = _id_token_sub(token)
    if not sub:
        raise HTTPException(502, "could not identify the Volvo account")

    with session_scope() as session:
        user = session.scalar(select(User).where(User.volvo_sub == sub))
        if user is None:
            user = User(volvo_sub=sub)
        user.primary_vin = vins[0] if vins else user.primary_vin
        store_token(session, user, token)
        session.flush()
        pairing = new_pairing_code()
        session.add(PairingCode(code=pairing, user_id=user.id))
        vin_display = user.primary_vin or "(no vehicle found)"

    return _page(
        "VolvoWatch — paired",
        '<div class="blueprint" style="padding: 26px">'
        '<div style="font-family: var(--font-heading); font-size: 12px; '
        'letter-spacing: 0.08em; text-transform: uppercase; '
        'color: var(--color-neutral-600); margin-bottom: 14px">Pairing</div>'
        "<h3 style=\"font-size: 26px; margin: 0 0 8px\">Almost done</h3>"
        f'<p style="margin: 0 0 6px; color: var(--color-neutral-800)">Connected to '
        f'<code style="font-family: ui-monospace, monospace; '
        f'background: var(--color-accent-100); padding: 1px 5px">'
        f"{html.escape(vin_display)}</code>.</p>"
        '<p style="margin: 0 0 16px; color: var(--color-neutral-800)">Open the '
        "VolvoWatch settings in the Garmin Connect app and enter this pairing "
        "code:</p>"
        '<div style="border: 1px solid var(--color-accent); '
        "background: var(--color-accent-100); padding: 20px; text-align: center; "
        "font-family: var(--font-heading); font-size: 40px; letter-spacing: 0.3em; "
        f'font-weight: 700; color: var(--color-accent-900)">{pairing}</div>'
        '<p style="margin: 14px 0 0; font-size: 13px; color: var(--color-neutral-600)">'
        "The code is valid for 15 minutes and can be used once.</p>"
        '<i class="corner tl"></i><i class="corner tr"></i>'
        '<i class="corner bl"></i><i class="corner br"></i>'
        "</div>",
        crumb="Paired",
    )


def _id_token_sub(token) -> str | None:
    raw = getattr(token, "id_token", None)
    if not raw:
        return None
    try:
        payload = raw.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("sub")
    except (IndexError, binascii.Error, ValueError, json.JSONDecodeError):
        return None
