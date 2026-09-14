# VolvoWatch — Privacy Policy

_Effective 2026-09-03. Contact: iot@tallimedia.com_

This policy explains what the app stores and why. It is run by a private
individual, not a company.

## What is stored

- **Volvo OAuth tokens** — an access token and a refresh token for your Volvo ID,
  so the app can read your vehicle data and send commands without asking you to
  sign in every time. The refresh token is encrypted at rest.
- **Your VIN** and a Volvo account identifier, to know which vehicle to query.
- **A device token** for each Garmin watch you pair, stored only as a hash.
- **A short-lived cache** (about one minute) of the vehicle status last fetched
  from Volvo.

Vehicle data (fuel, battery, range, lock state, service intervals and, if you
enable it later, location) passes through the backend to your watch. It is not
sold, shared, or used for any purpose other than serving it to your own paired
devices.

## Where it is stored

On a self-hosted server operated by the app author. No third-party analytics or
advertising services are used.

## Deleting your data

You can revoke the app's access at any time from your Volvo ID account settings.
To have stored tokens and identifiers deleted from the backend, contact the
address above.

## Third parties

The app communicates with the Volvo Cars API (subject to Volvo's own terms and
privacy policy) and with Garmin's Connect IQ platform, which relays requests
between your watch and the backend.
