# scripts/

One-off and scheduled maintenance scripts that aren't part of the FastAPI app itself.

## check_new_volvos.py

Daily Signal digest of new VolvoWatch pairings. Runs read-only against the
production `data/volvowatch.db`, compares today's user count to the count
stored in `.last_user_count` (gitignored, not this script), and sends one
Signal message only if the count went up — silent otherwise.

Uses the same `signal-api` bridge (alpine-docker, `10.10.20.136:8080`) every
other Signal alert in the house already goes through — same sender/recipient
number, read from Uptime Kuma's own notification config.

**Deployed on public-vm as a systemd timer**, not cron (not installed on
this Debian 13 box):

- `/etc/systemd/system/check-new-volvos.service` — runs
  `python3 scripts/check_new_volvos.py` once.
- `/etc/systemd/system/check-new-volvos.timer` — `OnCalendar=*-*-* 10:00:00
  Europe/Helsinki`, daily, DST-aware (public-vm itself runs in UTC).

To redeploy after an edit: `scp` the updated script to
`~/public-services/volvowatch/scripts/` on public-vm, no service restart
needed (the timer just runs the file fresh each day). To check status:
`systemctl list-timers check-new-volvos.timer`, `journalctl -u
check-new-volvos.service`.
