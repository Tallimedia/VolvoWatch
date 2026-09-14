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

router = APIRouter(tags=["auth"])

_log = logging.getLogger(__name__)


def _page(title: str, body: str) -> str:
    return f"""<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
 body{{font:16px/1.5 system-ui,sans-serif;margin:0;padding:2rem;
   background:#0b1020;color:#e7ecf5;display:flex;justify-content:center}}
 main{{max-width:26rem;width:100%}}
 h1{{font-size:1.3rem}}
 a.btn,button{{display:inline-block;background:#3b6ef0;color:#fff;border:0;
   border-radius:.6rem;padding:.8rem 1.2rem;font-size:1rem;text-decoration:none;cursor:pointer}}
 code{{background:#1c2540;padding:.15rem .4rem;border-radius:.3rem}}
 .code{{font-size:2.2rem;letter-spacing:.35rem;font-weight:700;background:#1c2540;
   padding:1rem;border-radius:.6rem;text-align:center;margin:1rem 0}}
 .muted{{color:#9fb0cc;font-size:.9rem}}
</style><main>{body}</main>"""


@router.get("/", response_class=HTMLResponse)
@router.get("/link", response_class=HTMLResponse)
async def link_landing() -> str:
    return _page(
        "VolvoWatch — connect",
        '<p class="muted">This page pairs a <b>Garmin watch</b> running the '
        "VolvoWatch app with your Volvo — it's not something you need unless "
        "you already have that app open on your wrist or phone.</p>"
        "<h1>Connect your Volvo</h1>"
        "<p>Sign in with your Volvo ID to let VolvoWatch read your car's status "
        "and start climatisation from your watch.</p>"
        '<p><a class="btn" href="/auth/login">Sign in with Volvo</a></p>'
        '<p class="muted">You sign in on Volvo\'s own site. This service never sees '
        "your password. Afterwards you'll get a short pairing code to enter in "
        "the watch app.</p>"
        '<p class="muted">Provided as-is with no SLA. Currently free; if that ever '
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
        "<h1>Almost done</h1>"
        f"<p>Connected to <code>{html.escape(vin_display)}</code>.</p>"
        "<p>Open the VolvoWatch settings in the Garmin Connect app and enter this "
        "pairing code:</p>"
        f'<div class="code">{pairing}</div>'
        '<p class="muted">The code is valid for 15 minutes and can be used once.</p>',
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
