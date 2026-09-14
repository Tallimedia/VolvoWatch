"""One-shot local OAuth helper for the Phase 0 spike.

Runs the authorization-code + PKCE flow against Volvo using a localhost redirect,
prints the access token, refresh token and id_token `sub`, and starts a tiny
loopback server to catch the callback.

    cd backend
    VOLVO_CLIENT_ID=... VOLVO_CLIENT_SECRET=... VOLVO_VCC_API_KEY=... \
        python spike/get_token.py

Requires the Volvo app to have redirect URI  http://localhost:8710/callback
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings  # noqa: E402
from app.pkce import code_challenge_s256, generate_code_verifier, generate_state  # noqa: E402
from app.volvo import VolvoClient  # noqa: E402

# Reads backend/.env via pydantic-settings, same as the server.
_settings = get_settings()

REDIRECT = "http://localhost:8710/callback"
SCOPES = _settings.scope_list

_code_holder: dict[str, str] = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        q = parse_qs(urlparse(self.path).query)
        _code_holder.update({k: v[0] for k, v in q.items()})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Got it - you can close this tab and return to the terminal.")

    def log_message(self, *_):  # silence
        return


async def main() -> None:
    _settings.require_volvo_credentials()
    client = VolvoClient(
        client_id=_settings.volvo_client_id,
        client_secret=_settings.volvo_client_secret,
        vcc_api_key=_settings.volvo_vcc_api_key,
        redirect_uri=REDIRECT,
    )
    verifier = generate_code_verifier()
    state = generate_state()
    url = client.authorize_url(
        scopes=SCOPES, state=state, code_challenge=code_challenge_s256(verifier)
    )
    print("Opening browser for Volvo consent...\n", url)
    webbrowser.open(url)

    server = HTTPServer(("localhost", 8710), Handler)
    while "code" not in _code_holder:
        server.handle_request()

    if _code_holder.get("state") != state:
        raise SystemExit("state mismatch")

    token = await client.exchange_code(code=_code_holder["code"], code_verifier=verifier)
    vins = await client.list_vehicles(token.access_token)

    print("\n--- TOKEN ---")
    print("access_token :", token.access_token)
    print("refresh_token:", token.refresh_token)
    print("expires_in   :", int(token.expires_at - time.time()), "s")
    print("scope        :", token.scope)
    print("vehicles     :", vins)


if __name__ == "__main__":
    asyncio.run(main())
