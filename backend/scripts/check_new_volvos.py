#!/usr/bin/env python3
"""Daily digest: how many new Volvos paired since yesterday, sent over Signal.

Run once a day (cron, see scripts/README.md). Compares the current row count
in the production users table against the count stored from the last run; if
it went up, sends one Signal message with the delta and the new total. If
nothing changed, stays silent — no message, no noise.

Uses the same signal-api bridge (alpine-docker, bbernhard/signal-cli-rest-api)
and number every other Signal alert in the house already goes through —
config read from Uptime Kuma's own notification setup on TrueNAS, not
reinvented here.
"""
from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "volvowatch.db"
STATE_PATH = Path(__file__).resolve().parent / ".last_user_count"

SIGNAL_URL = "http://10.10.20.136:8080/v2/send"
SIGNAL_NUMBER = "+358445948529"
SIGNAL_RECIPIENTS = ["+358445948529"]


def current_count() -> int:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        return con.execute("select count(*) from users").fetchone()[0]
    finally:
        con.close()


def last_count() -> int | None:
    if not STATE_PATH.exists():
        return None
    try:
        return int(STATE_PATH.read_text().strip())
    except ValueError:
        return None


def send_signal(message: str) -> None:
    body = json.dumps({
        "message": message,
        "number": SIGNAL_NUMBER,
        "recipients": SIGNAL_RECIPIENTS,
    }).encode()
    req = urllib.request.Request(
        SIGNAL_URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"signal-api returned {resp.status}")


def main() -> None:
    count = current_count()
    previous = last_count()

    # First run ever (no state file yet): just record the baseline, don't
    # fire a message claiming every existing Volvo is "new" today.
    if previous is not None and count > previous:
        new = count - previous
        plural = "Volvo" if new == 1 else "Volvos"
        try:
            send_signal(f"{new} new {plural} registered. Total: {count}.")
        except (urllib.error.URLError, RuntimeError) as exc:
            # Don't update the state file on a failed send — next run will
            # retry with the same delta instead of silently losing it.
            print(f"Signal send failed, will retry next run: {exc}")
            return

    STATE_PATH.write_text(str(count))


if __name__ == "__main__":
    main()
