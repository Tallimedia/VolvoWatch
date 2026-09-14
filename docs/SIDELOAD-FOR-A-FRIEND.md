# Sideloading the app for someone else

A Connect IQ **beta is not shareable** — Garmin gives no tester list or
invites, only the uploading account's own devices can install it. Sideloading
is how anyone else gets the app.

A sideloaded app has **no settings screen** (Garmin serves settings metadata
from the store), so there's nowhere to type a pairing code in Garmin Connect
Mobile — but the watch itself has a fallback: the action menu's **"Enter
pairing code"** opens a digit-wheel code picker right on the device. No
credential needs to be compiled into the build, and the same `.prg` works for
anyone on a supported watch model.

---

## 1. Build a plain `.prg`

`source/DevConfig.mc` should already be blank (`DEVICE_TOKEN`/`CAR_LABEL`
both `""`) — that's the normal state, kept out of git via `skip-worktree`.
If it isn't, blank it first.

```bash
cd watch
export JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$HOME/Library/Application Support/Garmin/ConnectIQ/Sdks/current/bin:$PATH"

monkeyc -f monkey.jungle -o bin/volvowatch.prg \
    -y ~/.garmin-ciq/developer_key.der -d fenix847mm -r
```

Swap `fenix847mm` for whatever device id matches their watch — see
`manifest.xml`'s `<iq:products>` for the full supported list. No live
credential is in this file, so it's safe to send however's convenient.

## 2. They install it (their computer + watch by USB)

- **Windows:** plug the watch in, it mounts as a drive. Copy `volvowatch.prg`
  into `GARMIN\APPS\`. Eject, unplug.
- **macOS:** newer Garmin watches use MTP, which the Finder can't mount.
  Install a client — `brew install --cask openmtp` (or Android File Transfer)
  — then copy `volvowatch.prg` into `GARMIN/APPS/`. Eject, unplug.

The app appears in the glance carousel and the app list, unpaired.

## 3. They connect and pair (their phone, ~2 min)

1. They open the app on the watch and select "Enter pairing code" — or open
   `https://volvowatchapp.tallimedia.com/link` on their phone first.
2. On the connect page, they sign in with **their own** Volvo ID and approve.
   You never see their password, and they never need to give you anything —
   this is different from the old process, which required you to handle
   their pairing code.
3. They get a 6-character pairing code, valid 15 minutes, single-use — and
   type it directly into the watch's code wheels.

The watch exchanges the code once for a private device token, stored only on
their own device.

## 4. Updating later

Every change to the app means: rebuild the `.prg`, re-send it, they re-copy
it. Their pairing survives — the device token lives in `Application.Storage`,
untouched by a reinstall unless they wipe app data. There is no auto-update
for sideloads. Past a handful of people this stops being worth it — that's
when a public store listing (new app id, Garmin review) becomes the real
answer.
