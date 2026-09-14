"""Thin async client for the Volvo Cars OAuth + Connected Vehicle / Energy APIs.

Only the pieces VolvoWatch needs. Endpoint inventory and scope tiers are
documented in ../RESEARCH.md.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any

import httpx

AUTHORIZE_URL = "https://volvoid.eu.volvocars.com/as/authorization.oauth2"
TOKEN_URL = "https://volvoid.eu.volvocars.com/as/token.oauth2"
API_BASE = "https://api.volvocars.com"
API_STATUS_URL = (
    "https://public-developer-portal-bff.weu-prod.ecpaz.volvocars.biz/api/v1/backend-status"
)

CONNECTED = "/connected-vehicle/v2/vehicles"
ENERGY = "/energy/v2/vehicles"

# Reads are quick; commands block while Volvo waits for the car to answer.
READ_TIMEOUT_S = 30
COMMAND_TIMEOUT_S = 45

# watch command name -> Volvo command path segment (POST {CONNECTED}/{vin}/commands/{segment}).
# Segments verified against GET /commands on a real XC60 (2026-09-03).
COMMANDS: dict[str, str] = {
    "climate-start": "climatization-start",
    "climate-stop": "climatization-stop",
    # Release 2 (restricted scopes):
    "flash": "flash",
    "honk": "honk",
    "honk-flash": "honk-flash",
    "lock": "lock",
    "unlock": "unlock",
}

# watch command name -> the Volvo OAuth scope it needs. Checked against
# User.scopes (what was actually granted at /link consent) before a command
# is sent — the COMMANDS map above lists Release 2 names even though that
# scope request isn't live yet, so this is the actual gate until it is.
COMMAND_SCOPES: dict[str, str] = {
    "climate-start": "conve:climatization_start_stop",
    "climate-stop": "conve:climatization_start_stop",
    "flash": "conve:honk_flash",
    "honk": "conve:honk_flash",
    "honk-flash": "conve:honk_flash",
    "lock": "conve:lock",
    "unlock": "conve:unlock",
}


def has_command_scope(configured_scopes: str | None, command: str) -> bool:
    """True if `command` needs no particular scope, or the backend's own
    currently-configured VOLVO_SCOPES includes the one it needs.

    Deliberately checks the *server's* config, not User.scopes — Volvo's
    token response omits `scope` whenever it matches what was requested
    (RFC 6749 §5.1, "OPTIONAL if identical to the scope requested"), which
    is the normal case here, so User.scopes never actually gets populated
    in practice (confirmed against real production data 2026-09-13: both
    existing users have an empty User.scopes despite default-scope commands
    already working for them). Checking the server's own scope list instead
    is accurate as long as no user's consent predates a scope being added —
    which already matches the documented Release 2 rollout plan ("every
    user re-consents at /link" — see CHANGELOG.md).
    """
    required = COMMAND_SCOPES.get(command)
    return required is None or required in (configured_scopes or "").split()


class VolvoError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        needs_reconnect: bool = False,
        timed_out: bool = False,
    ):
        super().__init__(message)
        self.status = status
        self.needs_reconnect = needs_reconnect
        self.timed_out = timed_out


@dataclass
class Token:
    access_token: str
    refresh_token: str
    expires_at: float
    scope: str = ""
    id_token: str | None = None


class VolvoClient:
    def __init__(self, client_id: str, client_secret: str, vcc_api_key: str, redirect_uri: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._vcc_api_key = vcc_api_key
        self._redirect_uri = redirect_uri
        self._basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        # One shared connection pool for this client's lifetime — the
        # previous `async with httpx.AsyncClient(...)` per call opened a
        # fresh TCP+TLS handshake for every single request, including each
        # of the ~9 sequential calls build_status() makes per /v1/status
        # fetch. An absolute URL (the OAuth token endpoint) still overrides
        # base_url fine, so one client covers every request this class makes.
        self._http = httpx.AsyncClient(base_url=API_BASE, timeout=READ_TIMEOUT_S)

    # ── OAuth ──────────────────────────────────────────────────────────────
    def authorize_url(self, *, scopes: list[str], state: str, code_challenge: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return str(httpx.URL(AUTHORIZE_URL, params=params))

    async def exchange_code(self, *, code: str, code_verifier: str) -> Token:
        return await self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._redirect_uri,
                "code_verifier": code_verifier,
            }
        )

    async def refresh(self, refresh_token: str) -> Token:
        return await self._token_request(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        )

    async def _token_request(self, data: dict[str, str]) -> Token:
        try:
            resp = await self._http.post(
                TOKEN_URL,
                data=data,
                headers={
                    "Authorization": f"Basic {self._basic}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
        except httpx.TimeoutException as exc:
            raise VolvoError("timed out talking to Volvo ID", status=504, timed_out=True) from exc
        except httpx.HTTPError as exc:
            raise VolvoError(f"transport error to Volvo ID: {type(exc).__name__}") from exc
        if resp.status_code >= 400:
            needs_reconnect = data["grant_type"] == "refresh_token" and resp.status_code in (
                400,
                401,
            )
            raise VolvoError(
                f"token request failed: {resp.status_code} {resp.text[:300]}",
                status=resp.status_code,
                needs_reconnect=needs_reconnect,
            )
        body = resp.json()
        return Token(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token", data.get("refresh_token", "")),
            expires_at=time.time() + int(body["expires_in"]),
            scope=body.get("scope", ""),
            id_token=body.get("id_token"),
        )

    # ── Resource calls ─────────────────────────────────────────────────────
    async def _get(self, access_token: str, path: str) -> dict[str, Any]:
        try:
            resp = await self._http.get(path, headers=self._auth_headers(access_token))
        except httpx.TimeoutException as exc:
            raise VolvoError(f"timed out on {path}", status=504, timed_out=True) from exc
        except httpx.HTTPError as exc:
            raise VolvoError(f"transport error on {path}: {type(exc).__name__}") from exc
        return self._parse(resp, path)

    async def _post(self, access_token: str, path: str) -> dict[str, Any]:
        try:
            resp = await self._http.post(
                path,
                headers={
                    **self._auth_headers(access_token),
                    "Content-Type": "application/json",
                },
                json={},
                timeout=COMMAND_TIMEOUT_S,
            )
        except httpx.TimeoutException as exc:
            raise VolvoError(f"timed out on {path}", status=504, timed_out=True) from exc
        except httpx.HTTPError as exc:
            raise VolvoError(f"transport error on {path}: {type(exc).__name__}") from exc
        return self._parse(resp, path)

    def _auth_headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "vcc-api-key": self._vcc_api_key,
            "Accept": "application/json",
        }

    @staticmethod
    def _parse(resp: httpx.Response, path: str) -> dict[str, Any]:
        if resp.status_code == 401:
            raise VolvoError(f"401 from {path}", status=401, needs_reconnect=True)
        if resp.status_code == 429:
            raise VolvoError(f"rate limited on {path}", status=429)
        if resp.status_code >= 400:
            raise VolvoError(
                f"{resp.status_code} from {path}: {resp.text[:300]}", status=resp.status_code
            )
        if not resp.content:
            return {}
        try:
            body = resp.json()
        except ValueError as exc:
            raise VolvoError(f"non-JSON response from {path}", status=502) from exc
        # Every endpoint we use returns an object; anything else is unexpected.
        return body if isinstance(body, dict) else {"data": body}

    async def list_vehicles(self, access_token: str) -> list[str]:
        data = await self._get(access_token, CONNECTED)
        items = data.get("data") or []
        if not isinstance(items, list):
            return []
        return [
            item["vin"] for item in items if isinstance(item, dict) and item.get("vin")
        ]

    async def fuel(self, access_token: str, vin: str) -> dict[str, Any]:
        return await self._get(access_token, f"{CONNECTED}/{vin}/fuel")

    async def odometer(self, access_token: str, vin: str) -> dict[str, Any]:
        return await self._get(access_token, f"{CONNECTED}/{vin}/odometer")

    async def statistics(self, access_token: str, vin: str) -> dict[str, Any]:
        return await self._get(access_token, f"{CONNECTED}/{vin}/statistics")

    async def doors(self, access_token: str, vin: str) -> dict[str, Any]:
        return await self._get(access_token, f"{CONNECTED}/{vin}/doors")

    async def windows(self, access_token: str, vin: str) -> dict[str, Any]:
        return await self._get(access_token, f"{CONNECTED}/{vin}/windows")

    async def diagnostics(self, access_token: str, vin: str) -> dict[str, Any]:
        return await self._get(access_token, f"{CONNECTED}/{vin}/diagnostics")

    async def tyres(self, access_token: str, vin: str) -> dict[str, Any]:
        return await self._get(access_token, f"{CONNECTED}/{vin}/tyres")

    async def command_accessibility(self, access_token: str, vin: str) -> dict[str, Any]:
        return await self._get(access_token, f"{CONNECTED}/{vin}/command-accessibility")

    async def energy_state(self, access_token: str, vin: str) -> dict[str, Any]:
        return await self._get(access_token, f"{ENERGY}/{vin}/state")

    async def send_command(self, access_token: str, vin: str, command: str) -> dict[str, Any]:
        if command not in COMMANDS:
            raise VolvoError(f"unknown command {command!r}", status=400)
        return await self._post(access_token, f"{CONNECTED}/{vin}/commands/{COMMANDS[command]}")


async def api_status() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as http:
        resp = await http.get(API_STATUS_URL)
    resp.raise_for_status()
    return resp.json()
