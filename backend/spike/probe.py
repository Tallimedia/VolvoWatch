"""Phase 0 endpoint probe.

Refreshes an access token from a saved refresh token, then calls every Release 1
endpoint against your VIN and pretty-prints the raw JSON — so we can pin the
actual field names/shapes and fix app/service.py.

    cd backend
    echo "<refresh_token>" > spike/.refresh_token      # from get_token.py
    python spike/probe.py                               # read + probe
    python spike/probe.py --climate-start               # also fire the command
    python spike/probe.py --loop 30                     # refresh every 30 min,
                                                        # to learn refresh-token lifetime

The refresh token rotates on each use — this script writes the new one back to
the file.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings  # noqa: E402
from app.volvo import COMMANDS, VolvoClient, VolvoError  # noqa: E402

TOKEN_FILE = Path(__file__).with_name(".refresh_token")

READS = [
    ("vehicle_details", "{vin}"),
    ("fuel", "{vin}/fuel"),
    ("energy_state", None),  # special: energy/v2
    ("statistics", "{vin}/statistics"),
    ("odometer", "{vin}/odometer"),
    ("doors", "{vin}/doors"),
    ("windows", "{vin}/windows"),
    ("diagnostics", "{vin}/diagnostics"),
    ("warnings", "{vin}/warnings"),
    ("tyres", "{vin}/tyres"),
    ("engine", "{vin}/engine"),
    ("engine_status", "{vin}/engine-status"),
    ("brakes", "{vin}/brakes"),
    ("commands", "{vin}/commands"),
    ("command_accessibility", "{vin}/command-accessibility"),
]


def _dump(name: str, payload) -> None:
    print(f"\n=== {name} " + "=" * (60 - len(name)))
    print(json.dumps(payload, indent=2, sort_keys=True))


async def probe_once(client: VolvoClient, refresh_token: str, *, climate_start: bool) -> str:
    token = await client.refresh(refresh_token)
    TOKEN_FILE.write_text(token.refresh_token + "\n")
    at = token.access_token
    print(f"[{dt.datetime.now():%H:%M:%S}] refreshed OK — access token good for "
          f"{int(token.expires_at - time.time())}s; new refresh token saved")

    vins = await client.list_vehicles(at)
    print("vehicles:", vins)
    if not vins:
        return token.refresh_token
    vin = vins[0]

    from app.volvo import CONNECTED, ENERGY  # noqa: PLC0415

    for name, tmpl in READS:
        try:
            if name == "energy_state":
                payload = await client._get(at, f"{ENERGY}/{vin}/state")  # noqa: SLF001
            else:
                payload = await client._get(at, f"{CONNECTED}/{tmpl.format(vin=vin)}")  # noqa: SLF001
            _dump(name, payload)
        except VolvoError as exc:
            _dump(name, {"ERROR": str(exc), "status": exc.status})

    if climate_start:
        try:
            _dump("climatization-start", await client.send_command(at, vin, "climate-start"))
        except VolvoError as exc:
            _dump("climatization-start", {"ERROR": str(exc), "status": exc.status})
        print("\nknown command names:", sorted(COMMANDS))

    return token.refresh_token


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--climate-start", action="store_true", help="also POST climatization-start")
    ap.add_argument(
        "--loop", type=int, metavar="MIN", help="repeat every MIN minutes (refresh-lifetime test)"
    )
    args = ap.parse_args()

    s = get_settings()
    s.require_volvo_credentials()
    client = VolvoClient(
        s.volvo_client_id, s.volvo_client_secret, s.volvo_vcc_api_key,
        "http://localhost:8710/callback",
    )

    if not TOKEN_FILE.exists():
        raise SystemExit(f"put your refresh token in {TOKEN_FILE} first")
    refresh_token = TOKEN_FILE.read_text().strip()

    while True:
        try:
            refresh_token = await probe_once(
                client, refresh_token, climate_start=args.climate_start
            )
        except VolvoError as exc:
            print(f"[{dt.datetime.now():%H:%M:%S}] REFRESH FAILED: {exc} "
                  f"(needs_reconnect={exc.needs_reconnect})")
            if args.loop:
                print("stopping loop — re-run get_token.py to re-consent")
            raise SystemExit(1) from exc
        if not args.loop:
            return
        print(f"\nsleeping {args.loop} min…\n")
        await asyncio.sleep(args.loop * 60)


if __name__ == "__main__":
    asyncio.run(main())
