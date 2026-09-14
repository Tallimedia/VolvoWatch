# VolvoWatch — Connect IQ widget

Glance + 4-page widget. `manifest.xml` targets 70 products / 115 device SKUs —
every mainstream round-screen, glance-capable Garmin line (fenix 6/7/8/9,
epix 2, fenixe, venu 2/3, vivoactive 5/6, forerunner 165–970, Marq, Descent).
Talks to the backend at `https://volvowatchapp.tallimedia.com` by default (see
`../backend`) — a different backend can be set from the app's own settings.

## What it does (Release 1)

- **Glance:** car name, battery % (green while charging) + fuel % + combined
  range — from a cached `/v1/status`, refreshed when older than 5 min.
- **Status page:** hero range, battery/fuel, lock + "all closed" + service-due
  + charging flags, "Updated Xm ago".
- **Charging page:** battery % hero, AC/DC, time to full while plugged in.
- **Trip page:** odometer, average fuel consumption, both trip meters.
- **Warnings page:** doors/windows called out separately, service due, washer
  fluid, tyre pressure, or "No active warnings" — plus the app version in the
  footer, so you can confirm which build is actually installed.
- **Action menu** (press select/menu): Start climate (with a confirmation) /
  Refresh / Enter pairing code / **Open connect page** — the last one sends
  a phone notification that opens the backend's `/link` page. (Stop climate
  is temporarily hidden as of 1.2.0 — Volvo's API doesn't reliably execute
  it; see `CHANGELOG.md`.)
  in your browser, since the watch has no browser of its own.
- **Pairing:** enter the 6-char code from `…/link` either in the widget
  settings in Garmin Connect Mobile, or directly on the watch via the
  digit-wheel code picker (works even for a sideload with no settings
  screen). First run exchanges it via `POST /v1/pair` for a device token
  (kept in `Application.Storage`) and clears the code.

## Build

```bash
# one-time: JDK + SDK on PATH (already in ~/.zshrc)
export JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$HOME/Library/Application Support/Garmin/ConnectIQ/Sdks/current/bin:$PATH"

cd watch
monkeyc -f monkey.jungle -o bin/volvowatch.prg \
    -y ~/.garmin-ciq/developer_key.der -d fenix847mm -w
```

Or in VS Code: **Monkey C: Build Current Project** (the extension is installed;
point it at `~/.garmin-ciq/developer_key.der` when prompted).

## Run in the simulator

```bash
connectiq &                                   # launches the CIQ simulator GUI
monkeydo bin/volvowatch.prg fenix847mm
```

In the simulator: **Settings → Edit Persistent Storage / Properties** isn't
needed — use **File → Edit App Settings** to set `pairingCode` to a fresh code
from `https://volvowatchapp.tallimedia.com/link`. The simulator makes real web
requests over the host network, so it will show live car data.

## Sideload to a real quatix 8

> **A sideloaded app has no settings screen.** Garmin serves app-settings
> metadata from the store, so Garmin Connect shows nothing for an app that was
> copied on manually. That's fine for the pairing code — `PairEntry`/
> `CodePicker` is an on-watch fallback built for exactly this case (a row of
> digit wheels), reachable from the action menu whenever the app isn't
> paired yet. There's no on-watch way to set a car name, though — that still
> needs `source/DevConfig.mc`, or it just shows the generic "Volvo".

A plain build with a blank `DevConfig.mc` (the normal state — see the warning
at the top of that file) works for this: sideload it, then pair on the watch
itself once you have a code from `/link`. No credential gets compiled in, so
this `.prg` is safe to hand to someone else, unlike the token-baked variant
below.

```bash
monkeyc -f monkey.jungle -o bin/volvowatch.prg \
    -y ~/.garmin-ciq/developer_key.der -d fenix847mm -r
```

Only fill in `source/DevConfig.mc` (it's `skip-worktree`, so it won't be
committed) if you want to skip on-watch pairing entirely — a real device
token compiled in is a live credential for that car, so don't hand a `.prg`
built this way to anyone else:

```monkeyc
const DEVICE_TOKEN = "<a token from POST /v1/pair>";
const CAR_LABEL = "My XC60";
```

Then, either way:

1. Connect the watch by USB.
   - **fēnix 7 and newer (incl. quatix 8) use MTP**, which macOS can't mount
     natively. If nothing appears in `/Volumes`, install a client:
     `brew install --cask openmtp` (or Android File Transfer).
   - Older, mass-storage devices just mount as a normal drive.
2. Copy `bin/volvowatch.prg` into **`GARMIN/APPS/`** on the watch, eject
   safely, unplug. The app shows up in the glance carousel and the app list.

## Publish to the Connect IQ Store (beta)

A beta upload is what unlocks **real app settings** (Garmin serves settings
metadata from the store), so it's how you run the app properly on your own
watch. Beta apps get their own store id, aren't publicly listed, and can be
re-uploaded freely.

**Confirmed working on a quatix 8, 2026-09-04:** installed 0.1.0 from the beta
entry, the settings screen appeared in Garmin Connect Mobile, pairing by code
worked, and live car data came through. Some forum reports claim beta-app
settings don't show up in Garmin Connect Mobile (only via Garmin Express on
desktop) — that did not happen here.

> **A beta is not a way to share with testers.** Garmin: *"URLs to the beta will
> not be visible outside of your account."* There is no tester list and no
> invite mechanism — it is your account only. For other people you need either a
> **public listing**, or a sideloaded `.prg` per person with their own token in
> `DevConfig.mc` (and no settings screen). See `../docs/CONNECTING-A-CAR.md`.

```bash
./build-release.sh   # builds every product in the manifest and packages them
```

Upload `bin/volvowatch.iq` at **<https://apps-developer.garmin.com>** — the
developer dashboard moved there and is no longer reachable from `apps.garmin.com`
(that's the consumer store now). Sign in with the Garmin account, upload the
`.iq`, then add the description/screenshots once the binary validates.

`DevConfig.mc` must be back to `""` first — published builds must pair through
app settings rather than carrying a compiled-in device token.
**Use `build-release.sh`, not a raw `monkeyc` invocation** — it's the only
thing that actually enforces this (refuses to build if `DEVICE_TOKEN`/
`CAR_LABEL` are non-empty or `FAKE_FLAGS` is true); a hand-typed `monkeyc`
command has no such check and will happily package a live device token into
a store upload.

## Known TODO

- Release 2 actions (flash/honk/lock/unlock) once Volvo grants restricted scopes.
- Background temporal event to refresh the glance without opening the widget.
