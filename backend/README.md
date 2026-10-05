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
  commands aren't. **Corrected 2026-10-06**: Volvo's limit is 10 commands/min
  scoped per (Volvo ID, Client ID) pair, not a pool shared across the whole
  app — confirmed directly against Volvo's own docs. A misbehaving watch can
  only exhaust *its own* user's budget, not rate-limit anyone else. Real gap,
  smaller blast radius than previously written here: still worth a guard so
  one user doesn't spam their own 429s, not the app-wide risk this used to
  describe.
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
- **No stale-device cleanup.** `Device` rows are never removed — re-pairing the
  same physical watch (or abandoning one) just leaves the old row behind
  forever. Harmless today (70 devices across 57 users as of 2026-10-05, most
  of the multi-device accounts are known test pairings), but worth a cleanup
  script eventually. Plan, not yet built:
  - Key off `Device.last_seen_at` (stamped on every authenticated call via
    `resolve_device()` in `service.py`, so it's a real "last actually used"
    signal, not a guess) — a generous threshold (90 days+) to avoid catching
    a watch that's just been unused for a season.
  - Dry-run by default: print a report (device id, user_id, label,
    created_at, last_seen_at) to stdout, no deletes.
  - Only delete behind an explicit flag, and dump the doomed rows to a
    timestamped JSON file in `~/public-services/backups/` first (same spot
    as the DB snapshots) so a wrong run is recoverable without restoring the
    whole DB.
  - Deleting a `Device` row is independent of `User`/`primary_vin` — no
    cascade, so even an overly aggressive run can't touch car pairing.
  - Manual/occasional run, not a cron job, until there's real evidence of
    orphaned devices piling up.
