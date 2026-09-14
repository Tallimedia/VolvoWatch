# Connect IQ Store listing copy

Paste-ready text for <https://apps-developer.garmin.com>. Keep in sync with
`CHANGELOG.md`.

---

## Short description (≤50 chars)

```
Your Volvo's range, fuel and battery on your wrist
```

Alternatives, all within 50:

- `Volvo range, fuel, battery + remote climate start` (49)
- `Your Volvo at a glance. Start the heating too.` (46)
- `Check your Volvo and warm it up from your wrist` (47)

---

## Full description (≤4000 chars)

```
Your Volvo, on your wrist.

VolvoWatch puts your car's live status in the glance carousel and gives you a
status page, a charging page, a trip page and a warnings page — plus climate
control — without reaching for your phone.

STATUS AT A GLANCE
Combined petrol and electric range as a single number — labelled "km tot
range" on a plug-in hybrid, so it's clear the figure is both. Lock state,
whether every door and window is shut, and a service reminder when due.

CHARGING
Battery percentage, AC/DC, and time to full while plugged in — the battery
figure turns green the moment it's actively charging.

TRIP
A large odometer — handy when a fuel card asks for the mileage — average
fuel consumption, and both trip meters.

WARNINGS
A real list, not just an icon: doors and windows called out separately,
service due (with the distance remaining), washer fluid, tyre pressure — or
a plain "no active warnings" when everything's fine.

CLIMATE CONTROL
Start and stop climatisation from the watch, with a confirmation step so it
can't be triggered by accident. The app reports what the car actually
answered, not just that a command was sent.

BUILT FOR PLUG-IN HYBRIDS FIRST
Developed and tested against a PHEV. Everything above already works for any
Volvo with connected services, but pure-EV-specific detail (like charging-
curve data) is on the roadmap, not in this release.

WHAT THIS APP CAN AND CAN'T DO
VolvoWatch uses Volvo's Level 1 data — vehicle status and the one climate
command above. Level 2 actions (remote lock, unlock, flash the lights, honk)
need a separate, more restricted approval from Volvo and aren't implemented
yet. If you want remote lock/unlock today, it isn't there yet — planned for
later.

SETUP
1. Install the app. First launch asks you to connect.
2. Open the action menu (press select) → "Open connect page" — sends a
   notification to your phone. Or just open
   https://volvowatchapp.tallimedia.com/link directly in any browser.
3. Sign in with your Volvo ID. You sign in on Volvo's own page — this app
   never sees your password.
4. You'll get a short pairing code. Enter it in Garmin Connect Mobile's app
   settings, or directly on the watch with the on-screen code wheels.
5. The watch exchanges the code once for a private device token and starts
   showing your car.

The app talks to a backend over HTTPS rather than to Volvo directly (Volvo's
API credentials can't safely live inside a watch app). It comes configured
to use our own hosted backend, so most people never need to think about
this — the backend is open source if you'd rather run your own; see the repo.

REQUIREMENTS
• A Volvo with connected services (Volvo On Call, ~2010-2024, or a Google
  built-in car from 2020 on) and a Volvo ID with the car linked
• Your phone nearby, or the watch on WiFi — no LTE on this device, so it
  needs one of those to reach the backend

GOOD TO KNOW
• Readings are as fresh as the car's last check-in — a parked car can go
  hours between updates unless plugged in or recently driven, so the app
  always shows how old the data is.
• The climate command only works while the car is reachable; Volvo refuses
  it while someone's driving, and the app says so.
• Stopping climatisation is accepted, but the car generally finishes its
  pre-conditioning cycle anyway — the car's behaviour, not a bug. The Volvo
  app's own stop button does the same.
• No analytics, no third-party trackers.

ABOUT THE HOSTED SERVICE
The default backend runs on private infrastructure (Tallimedia), as-is with
no service-level agreement — no guaranteed uptime, and we're not responsible
for connectivity or hardware issues there. Full terms on the connect page.

An independent project, not affiliated with, endorsed by, or supported by
Volvo Cars. "Volvo" is a trademark of Volvo Trademark Holding AB. Built on
the public Volvo Cars Developer API.

Source and setup docs: https://github.com/tallimedia/VolvoWatch
```

---

## What's new / release notes (≤4000 chars)

### 1.1.0

```
Fixed a display bug on the status page: EV owners without a fuel tank were
seeing a stray "Fuel" reading with no value. The battery figure now shows
on its own when a car has no fuel data.
```

### 1.0.0

```
First public release. Range, fuel and battery at a glance, plus dedicated
Charging, Trip and Warnings pages, and climate control from your wrist —
built on a hosted backend, no setup beyond signing in with your Volvo ID.
```

---

## Notes for the upload form

- **Title:** `My Volvo Watch App`
  - Uses the Volvo brand, so the description carries an explicit
    "not affiliated with Volvo Cars" disclaimer. The leading "My" helps — it
    reads as a personal project rather than an official Volvo product.
  - The on-watch name stays the short `Volvo` (`@Strings.AppName`) so it fits
    the glance and app list.
- **Artwork:** `store/hero-1440x720.png` and `store/cover-500x500.png`, both
  regenerated by `python3 store/make_store_art.py`. The watch face in them is
  drawn from the same layout `MainView` uses, so the art can't drift from the
  app. The cover drops the two smallest lines to stay readable as a thumbnail.
- **Unit photos:** to be added later (real photos of the watch on-wrist).
- **Three fields, don't mix them up:** the short description (50 chars), the
  full description (setup + requirements + disclaimer), and the release notes
  ("what's new"). The release notes deliberately end by pointing at the
  description, so they are not interchangeable.
- **Version:** `1.1.0`
- **Type:** Widget (detected from the manifest)
- **Class / category:** Lifestyle (Finnish portal: *Elämäntyyli*; *Työkalut* =
  Tools, the fallback if Lifestyle isn't offered). The store's own bucket for
  this kind of app is "Life at a Glance".
- **Regional restriction:** Europe. Matches Volvo — its API only reaches
  cars in **EMEA**, so nothing is lost by restricting. Widen to Middle
  East / Africa only if someone there ever needs it.
- **Compatible devices:** auto-filled from `manifest.xml`'s 70 `<iq:product>`
  entries — 115 device SKUs (several ids alias multiple marketed names, e.g.
  `fenix847mm` covers fēnix 8 47/51 mm, tactix 8, and quatix 8 at once).
  Mainstream round-screen, glance-capable lines: fenix 6/7/8/9, epix 2,
  fenixe, venu 2/3, vivoactive 5/6, forerunner 165–970, Marq (all lines),
  Descent (G2/MK2/MK2S/MK3 43mm/MK3 51mm). Deliberately excludes Approach
  (golf) and D2 (aviation) as out of scope for this app's audience, and two
  Descent models for real technical reasons: `descentg1`'s screen isn't
  round (octagonal) and `descentmk1` predates Glance support (API 3.1, this
  app needs 3.4+). Verified 2026-09-13: all 115 SKUs build clean (only
  benign launcher-icon auto-scale warnings — the 65×65 source icon gets
  scaled to whatever each device wants, 40–70px; fine as a fallback, a
  multi-resolution icon set would look crisper if ever revisited).
- **Screenshots.** The store does **not** add a device frame to uploaded images,
  so a bare 454×454 capture shows as a flat black square. Workflow:
  1. In the sim, `File → Save Screen Capture`, drop it in `store/` as
     `capture-<n>-<name>.png` (gitignored).
  2. `python3 store/make_store_art.py` frames each `capture-*.png` into the
     watch bezel → `store/screenshot-*.png` (720×720, committed). The glance
     shot is the one exception — it's hand-composited by
     `make_glance_screenshot()` instead of framed from a raw capture (see
     that function's docstring: a plain capture only has the bare content
     GlanceView draws, not the system's own highlighted-row/app-icon chrome
     around it).
  - `screenshot-1-status.png` — status screen (coloured battery, "km tot range",
    the icon row). **Primary.**
  - `screenshot-2-status-inuse.png` — status screen while the car reports
    `CAR_IN_USE` (steering-wheel icon instead of the charging bolt).
  - `screenshot-3-charging.png` — Charging page, actively charging (AC, time
    to full).
  - `screenshot-4-trip.png` — Trip page (odometer, avg fuel, trip meter).
  - `screenshot-5-warnings.png` — Warnings page with active warnings.
  - `screenshot-6-menu.png` / `screenshot-7-menu2.png` — the action menu,
    top and bottom half (start/stop climate, refresh, enter pairing code —
    doesn't fit in one screen on a round display).
  - `screenshot-8-glance.png` — the glance-carousel card.
- This is a normal public listing, not a Beta — anyone can find and install it.
