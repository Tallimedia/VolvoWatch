# Connecting a Volvo to VolvoWatch

How anyone links their own Volvo to the app. Nothing needs doing in the Volvo
developer portal by the person connecting a car — they only grant consent
with their own Volvo ID, on Volvo's own sign-in page.

## What you need

- A **Volvo ID** (the same account used in the Volvo Cars mobile app) with
  your car showing up in that app. If the car isn't in the Volvo Cars app,
  it won't be reachable through this API either.
- Your car in a supported region (Europe / Middle East / Africa).
- A phone with **Garmin Connect Mobile**, and the VolvoWatch app on your
  watch — installed from the Connect IQ Store, or sideloaded (see
  `SIDELOAD-FOR-A-FRIEND.md` if someone's handing you a `.prg` directly
  instead of a Store listing).

## Steps

1. **Open the connect page**: `https://volvowatchapp.tallimedia.com/link` —
   or, on the watch, open the action menu (press select) → "Open connect
   page", which sends a notification to your phone that opens the same page.
2. Tap **"Sign in with Volvo"**. You're taken to **volvocars.com** — Volvo's
   own login page, not this app's.
3. Sign in with **your** Volvo ID and password.
4. **Review and approve** the permissions. VolvoWatch asks to read: fuel,
   battery/energy, range, odometer, doors/windows, lock status, service
   info, warnings, tyres, trip statistics — and to **start/stop
   climatisation**. It does **not** ask to unlock, honk, flash, or locate
   the car — those need a separate, more restricted Volvo approval this app
   doesn't have yet.
5. The page shows a **6-character pairing code** (valid 15 minutes, one
   use).
6. Enter it either in **Garmin Connect Mobile → the VolvoWatch app →
   Settings → Pairing code**, or directly on the watch via the digit-wheel
   code picker (action menu → "Enter pairing code").
7. The watch exchanges the code once for a private device token and starts
   showing your car.

To revoke access later: in your Volvo ID account settings, remove
VolvoWatch's access. That immediately stops the backend from reaching your
car.

## What the backend stores

- Each consent creates one `users` row keyed by the Volvo account id
  (`sub`), holding that person's encrypted refresh token and their
  `primary_vin` (auto-discovered from Volvo's API — nobody types a VIN by
  hand).
- Your Volvo password is never seen by this app or its backend — only the
  OAuth tokens Volvo issues after you sign in on Volvo's own page.
- Everyone's polling shares the backend's Volvo API key and its daily call
  budget. At a 60s status cache and a 5min glance refresh that's roughly a
  few hundred calls/day per active watch.

## Troubleshooting

- **"unknown or expired login attempt"** on the callback page — the OAuth
  state expired (10 min). Start again from `/link`.
- **Pairing code rejected on the watch** — codes last 15 minutes and are
  single-use; generate a fresh one from `/link`.
- **App shows "reconnect Volvo"** — the refresh token expired or was
  revoked; run `/link` again to re-consent.
- **Data shows stale / "updated 3h ago"** — normal when parked; the car
  only reports in periodically unless plugged in or recently driven.
- **Commands fail with `CAR_IN_USE`** — someone is driving it; Volvo blocks
  remote commands while that's true, and the app says so.
