# VolvoWatch — watch app changelog

Versions here match what's entered in the **Connect IQ Store upload form**
(<https://apps-developer.garmin.com>). The store requires each upload to have a
higher version than the last.

## 1.1.0 — pure-EV fix

- Status page no longer shows a stray "Fuel –" on a pure EV. Volvo reports
  `fuelAmount: null` (not `0`) for cars with no tank, and the status page
  drew the "Fuel" label unconditionally regardless — now it's only shown
  alongside a real fuel reading, same as the glance card and Trip page
  already did. Found via real feedback from the first pure-EV tester.

## 1.0.0 — first public release

- Status page: combined petrol + electric range, lock state, doors/windows,
  service reminder.
- Charging page: battery %, AC/DC, time to full — the battery figure turns
  green while actively charging.
- Trip page: odometer, average fuel consumption, both trip meters.
- Warnings page: doors/windows called out separately, service due, washer
  fluid, tyre pressure, or "No active warnings".
- Climate control: start/stop climatisation with a confirmation step,
  reporting what the car actually answered.
- Glance card: car name, battery (green while charging), fuel, range.
- Action menu: Start/Stop climate, Refresh, Enter pairing code, Open connect
  page (sends a phone notification that opens the sign-in page — the watch
  has no browser of its own).
- Pairing: sign in with your Volvo ID at `/link`, then enter the resulting
  code either in Garmin Connect Mobile's app settings or directly on the
  watch via the digit-wheel code picker.
- Runs against a hosted backend by default — no self-hosting required,
  though the backend is open source if you'd rather run your own instance.
- 115 device SKUs supported — every mainstream round-screen, glance-capable
  Garmin line (fenix 6/7/8/9, epix 2, fenixe, venu 2/3, vivoactive 5/6,
  forerunner 165–970, Marq, Descent).

Built and tested against a plug-in hybrid (PHEV) first — pure-EV-specific
detail is planned, not yet built. Uses Volvo's default-scope ("Level 1")
API: vehicle status and climate control. Restricted-scope actions (remote
lock/unlock, flash, honk) need separate Volvo approval and aren't
implemented yet.
