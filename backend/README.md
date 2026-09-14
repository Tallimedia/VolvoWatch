# VolvoWatch backend

FastAPI proxy: holds the Volvo Cars OAuth tokens, refreshes them, and exposes a
small REST API to the Garmin watch.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/link` | — | Landing page → "Sign in with Volvo" |
| GET | `/auth/login` | — | Start OAuth (PKCE), redirect to Volvo |
| GET | `/auth/callback` | — | Volvo redirect target → shows a pairing code |
| POST | `/v1/pair` | pairing code | Exchange code for a long-lived device token |
| GET | `/v1/status` | device token | Compact vehicle status (cached ~60 s) |
| POST | `/v1/command/{name}` | device token | `climate-start`,`climate-stop` (R1); `flash`,`honk`,`honk-flash`,`lock`,`unlock` (R2) |
| GET | `/v1/command/{invoke_id}` | device token | Command status (stub — see code note) |
| GET | `/v1/devices` | device token | List watches paired to this Volvo ID |
| GET | `/healthz`, `/volvo-status` | — | Liveness + Volvo API status passthrough |

## Local run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
python -m app.cli gen-keys           # paste FERNET_KEY + DEVICE_TOKEN_PEPPER into .env
# add VOLVO_CLIENT_ID / _SECRET / _VCC_API_KEY from the Volvo portal
python -m app.cli show-config        # sanity check
uvicorn app.main:app --reload --port 8000
pytest
```

For local OAuth, register `http://localhost:8000/auth/callback` as a redirect URI
on the Volvo app (multiple URIs are allowed; add the prod one too).

## Spike scripts

`spike/get_token.py` runs the whole OAuth flow from the CLI and prints tokens.
`spike/volvo.http` is a request collection for poking the Volvo API by hand and
for measuring token lifetimes. Useful for debugging against a real Volvo
account without going through the watch.

## Deploy

Docker Compose behind a reverse proxy (Traefik) and a Cloudflare Tunnel — no
public IP or open ports needed. Set `.env`'s `VOLVO_REDIRECT_URI` and
`PUBLIC_BASE_URL` to your public HTTPS hostname. Full steps: `DEPLOY.md`.

## Known gaps

Rate limiting on `/v1/pair`, the command scope-gate, `InvalidToken` handling,
the VIN-collision auth fallback, status-cache keying/eviction, connection
pooling, and SQL-based `purge_expired()` are all done. What's still actually
open:

**Before opening this beyond friends & family:**
- **No per-device rate limiting on `/v1/command`.** `/v1/pair` is rate-limited;
  commands aren't. Volvo allows ~10 commands/min *per API key*, so one
  misbehaving watch can rate-limit every user.
- **OAuth `state` isn't bound to a browser session** (no cookie), which allows
  login-CSRF: a victim could be walked through completing an attacker's flow and
  end up paired to the attacker's car. Low impact today (no user accounts).
- **`id_token` `sub` is decoded without signature verification** — verify against
  Volvo's JWKS before trusting it as the primary user key.
- `FUEL_TANK_LITRES` is global, not per-vehicle.

**Operational:**
- No DB migrations — `create_all` won't alter existing tables. Back up
  `data/volvowatch.db` and migrate by hand before changing a model.
- The Fernet key and the device-token pepper both live in `.env`, so a `.env`
  leak defeats both at-rest protections. Inherent to single-host deployment.
- Volvo's `access_token` is stored unencrypted (the refresh token is encrypted);
  it's 5-minute-lived, but it's inconsistent.
- The watch doesn't pre-check `/command-accessibility` before sending a command.
