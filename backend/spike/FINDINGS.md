# Phase 0 findings — Volvo API against a real car

Source: `spike/get_token.py` + `spike/probe.py` against a **2024 Volvo XC60 PHEV
(T8)**, market FI, on 2026-09-03. VINs/tokens redacted here.

## OAuth

- Flow: authorization code + PKCE, `client_type: CONFIDENTIAL` (client secret
  required, sent as HTTP Basic on the token endpoint). Confirms the backend is
  mandatory — the secret can't ship in the watch app.
- **Access token TTL: exactly 300 s (5 min).** `exp - iat = 300` in the JWT.
- Refresh token: **rotates on every use** — the new one must be persisted each
  time. Lifetime TBD — run `python spike/probe.py --loop 30` for a few days.
- `id_token` is returned (scope `openid`); the access token itself is also a JWT
  carrying `sub` (stable per-user id) and the granted `scope` list.
- Token response does **not** echo a top-level `scope` field — read scopes from
  the JWT if needed. All 19 requested scopes were approved.
- `redirect_uri` must match a registered URI exactly. `localhost` URIs work.

## API version audit (2026-09-04)

Cross-checked our client against **`volvocarsapi` 0.4.4** (2026-08-21 — the
library behind the official Home Assistant Volvo integration, actively tracking
the portal):

- **Connected Vehicle API — `/connected-vehicle/v2/`** — current, no v3 exists.
  We're on v2. ✓
- **Energy API — `/energy/v2/vehicles/{vin}/state` + `/capabilities`** — current.
  `/energy/v1/` still exists but only for the legacy `recharge-status` shape;
  v2 `/state` is what the library prefers and what we use. ✓
- **Location API — `/location/v1/`** — v1, we don't use it.
- **Extended Vehicle API — sunset 2025-12-31** — we never used it, nothing to migrate.
- **No climatization *status* endpoint at any version.** `/…/climatization` and
  `/climatization/v1/…` are 404. Only `commands/climatization-start|stop`.

Verdict: backend is on the latest API versions. The only unused-but-current
endpoints are `brakes`, `engine` (warnings), `warnings` (bulb-outs) — the
"faults field" backend TODO, not a version gap.

## Endpoint shapes (vs. the original guesses in service.py)

| Endpoint | Wrapper | Notes |
|---|---|---|
| `/connected-vehicle/v2/.../*` | `{"data": {...}}` | each value `{value, timestamp, unit}` |
| `/energy/v2/vehicles/{vin}/state` | **no wrapper** | each value `{value, status, updatedAt, unit}`; unsupported props come back as `{code, message, status:"ERROR"}` |

Concrete corrections applied to `app/service.py`:

- **Lock:** `doors.centralLock` (not `carLocked`), values `LOCKED` / `UNLOCKED`.
- **Doors/windows open:** value is `CLOSED` / (presumably `OPEN`/`AJAR`).
- **`diagnostics.timeToService` unit is `months`** (not days). `distanceToService`
  can be `0` = due now. `serviceWarning` values: `NO_WARNING`,
  `DISTANCE_DRIVEN_TIME_FOR_SERVICE`, …
- **Fuel:** `/fuel` gives `fuelAmount` (litres) + `batteryChargeLevel` (%). **No
  fuel percentage** — derive from `FUEL_TANK_LITRES` if wanted, else show litres
  / range. `distanceToEmptyTank` lives in `/statistics`, not `/fuel`.
- **Energy:** `chargerConnectionStatus` = `CONNECTED` / `DISCONNECTED`;
  `chargingStatus` = `IDLE` / (`CHARGING`/`DONE`/`SCHEDULED`/`FAULT`?);
  `chargingType` = `AC` / `DC` / `NONE`. `chargingPower`,
  `chargingCurrentLimit` return `ERROR` on this car — must be tolerated.
- **`command-accessibility`:** `data.availabilityStatus.{value, unavailableReason}`.
  Seen: `UNAVAILABLE` / `CAR_IN_USE` while driving. Gate command UI on this.
- **`/brakes` → 403** — needs `conve:brake_status`, which we didn't request. Not
  needed for Release 1.

## Commands supported by this VIN (`GET /commands`)

`LOCK`, `LOCK_REDUCED_GUARD`, `UNLOCK`, `ENGINE_START`, `ENGINE_STOP`, `HONK`,
`HONK_AND_FLASH`, `FLASH`, `CLIMATIZATION_START`, `CLIMATIZATION_STOP`.

- **`HONK_AND_FLASH` path segment is `honk-flash`** (not `honk-and-flash`) —
  fixed in `volvo.COMMANDS`.
- **`climatization-start` confirmed end-to-end (2026-09-03)** — the car started
  climatisation. `climatization-stop` also returns HTTP 200.
- **Command response shape:** `{"data": {"invokeStatus": "COMPLETED", "message":
  "", "vin": "..."}}`. Field is `invokeStatus` (not `invokeId`/`status`). Values
  seen: `COMPLETED`. Others per Volvo docs: `DELIVERED`, `WAITING`, `RUNNING`,
  `REJECTED`, `TIMEOUT`, `FAILED`, `NOT_ALLOWED`, `UNKNOWN`, `CONNECTION_FAILURE`.
- **`climatization-stop` returns `COMPLETED` but the car may keep running its
  pre-conditioning cycle** (2026-09-04) — once started, the XC60 PHEV tends to
  run climatisation to completion regardless; the stop command is accepted but
  not honoured mid-cycle. Same behaviour as the Volvo app's stop button. Not a
  transport/API bug — nothing to fix on our side.

## Parked-state probe (2026-09-03, climate running)

- `command-accessibility` → `value: "AVAILABLE"`, `unavailableReason: null`.
- **No "climatisation active" field** anywhere in the Release 1 endpoint set —
  the API doesn't expose HVAC state. `engineStatus` stays `STOPPED` with electric
  climate on a PHEV. The watch fires the command and trusts the accepted result;
  no way to reflect "climate is on" from polling.
- **Re-confirmed 2026-09-04** with climate genuinely running (Nico started it
  from the Volvo app, not the watch). Probed every plausible endpoint:
  `engine-status` (`STOPPED`), `engine`, `command-accessibility` (`AVAILABLE`),
  `commands` (only START/STOP, no status), `warnings`, `diagnostics`,
  `statistics`, `energy/v2/state` (no climate field), `energy/v2/capabilities`.
  Tried `/connected-vehicle/v2/vehicles/{vin}/climatization`,
  `/climatization/v1/...` — **all 404, the resource does not exist.** Only fresh
  timestamps on the ~11:42 partial check-in were `engineStatus`,
  `command-accessibility`, `batteryChargeLevel`, `electricRange` — none of which
  say anything about HVAC. A "Climate ON" indicator can only be backend-synthetic
  (stamp the start, assume a ~30-min window).
- Also seen this probe: `batteryCapacityKWH: 18.819`, `averageEnergyConsumption`
  `0.1 kWh/100km` (junk on a PHEV — right call to skip it),
  `averageFuelConsumptionAutomatic: 10.3` vs manual `10.5`.
- `serviceWarning` has an **`DISTANCE_DRIVEN_OVERDUE_FOR_SERVICE`** variant (seen
  alongside the earlier `..._TIME_FOR_SERVICE`). `service_due` catches both; a
  future UI could split "due" vs "overdue".
- Idling with climate burned ~4 L in ~25 min and dropped `distanceToEmptyTank`
  270 → 250 — data refreshes quickly while the car is active.

## Still open

- Real refresh-token lifetime (the suspected ~7-day expiry) — `probe.py --loop`.
- Whether a *different* Volvo ID can consent to this unpublished app (needed for
  friends & family) — test with a second account. See `docs/CONNECTING-A-CAR.md`.
- Whether Volvo commands expose any status-by-id polling (looks fire-and-forget).
