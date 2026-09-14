"""Terms of Service + Privacy Policy pages.

Referenced from the Volvo API application registration and shown on the OAuth
consent screen. DRAFT — review and adjust the contact details and specifics
before submitting the app for Volvo publishing / opening it beyond yourself.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["legal"])

_CONTACT = "iot@tallimedia.com"
_EFFECTIVE = "2026-09-13"

_STYLE = """
<style>
 body{font:16px/1.6 system-ui,sans-serif;margin:0;padding:2rem;background:#0b1020;color:#e7ecf5}
 main{max-width:44rem;margin:0 auto}
 h1{font-size:1.4rem} h2{font-size:1.05rem;margin-top:1.8rem}
 a{color:#7aa2ff} .muted{color:#9fb0cc;font-size:.9rem}
 code{background:#1c2540;padding:.1rem .35rem;border-radius:.3rem}
 .back{display:inline-block;margin-bottom:1.2rem}
</style>
"""


def _wrap(title: str, body: str) -> str:
    return (
        f"<!doctype html><meta charset=utf-8>"
        f'<meta name=viewport content="width=device-width,initial-scale=1">'
        f"<title>{title} — VolvoWatch</title>{_STYLE}<main>"
        f'<a class="back" href="/">&larr; Back to home</a>{body}'
        f'<p class="muted">Effective {_EFFECTIVE}. Contact: '
        f'<a href="mailto:{_CONTACT}">{_CONTACT}</a>.</p></main>'
    )


@router.get("/terms", response_class=HTMLResponse)
async def terms() -> str:
    return _wrap(
        "Terms of Service",
        """
<h1>VolvoWatch — Terms of Service</h1>
<p>VolvoWatch is an independent, non-commercial hobby project that shows your
Volvo vehicle information on a Garmin watch and lets you send a limited set of
remote commands (such as starting climatisation). It is
<strong>not affiliated with, endorsed by, or supported by Volvo Cars</strong>.
"Volvo" is a trademark of Volvo Trademark Holding AB. VolvoWatch is built on
the public Volvo Cars Developer API.</p>

<h2>Use of the app</h2>
<p>You may use the app only with a Volvo vehicle you are authorised to access,
and only by granting consent through your own Volvo ID, on Volvo's own
sign-in page — this service never sees your Volvo password. You are
responsible for anything done with your account through the app, including
remote commands you trigger.</p>

<h2>Service availability</h2>
<p>This service is run on a best-effort basis, with <strong>no service-level
agreement (SLA)</strong> — no guaranteed uptime, response time, or support
commitment. It may be unavailable during maintenance, hosting-provider
outages, or Volvo API issues outside our control, and it may be changed or
discontinued at any time with reasonable notice.</p>

<h2>Fees</h2>
<p>VolvoWatch is currently free to use. That may change: a fee or
subscription could be introduced for this service at any time, and doing so
does not require asking existing users first. That said, <strong>nothing
will ever be charged to you without your explicit acceptance</strong> at the
time — no silent or automatic billing. If you don't accept a fee that's
introduced later, your access may simply end rather than be charged for.</p>

<h2>No warranty</h2>
<p>The app is provided "as is", with no warranty of any kind. Vehicle data may be
delayed, incomplete, or unavailable, and commands may fail or be delayed. Do not
rely on the app for anything safety-critical. The app depends on the Volvo Cars
API and may stop working if that API changes or access is withdrawn.</p>

<h2>Limitation of liability</h2>
<p>To the maximum extent permitted by law, the operator of the app is not liable
for any loss or damage arising from use of, or inability to use, the app.</p>

<h2>Changes</h2>
<p>These terms may change. Continued use after a change means you accept the
updated terms.</p>
""",
    )


@router.get("/privacy", response_class=HTMLResponse)
async def privacy() -> str:
    return _wrap(
        "Privacy Policy",
        """
<h1>VolvoWatch — Privacy Policy</h1>
<p>This policy explains what the app stores and why. It is run by a private
individual, not a company.</p>

<h2>What is stored</h2>
<ul>
<li><b>Volvo OAuth tokens</b> — an access token and a refresh token for your
Volvo ID, so the app can read your vehicle data and send commands without asking
you to sign in every time. The refresh token is encrypted at rest.</li>
<li><b>Your VIN</b> and a Volvo account identifier, to know which vehicle to
query.</li>
<li><b>A device token</b> for each Garmin watch you pair, stored only as a
hash.</li>
<li><b>A short-lived cache</b> (about one minute) of the vehicle status last
fetched from Volvo.</li>
</ul>
<p>Vehicle data (fuel, battery, range, lock state, service intervals and, if you
enable it later, location) passes through the backend to your watch. It is not
sold, shared, or used for any purpose other than serving it to your own paired
devices.</p>

<h2>Where it is stored</h2>
<p>On a self-hosted server operated by the app author. No third-party analytics
or advertising services are used.</p>

<h2>Deleting your data</h2>
<p>You can revoke the app's access at any time from your Volvo ID account
settings. To have stored tokens and identifiers deleted from the backend, contact
the address below.</p>

<h2>Third parties</h2>
<p>The app communicates with the Volvo Cars API (subject to Volvo's own terms and
privacy policy) and with Garmin's Connect IQ platform, which relays requests
between your watch and the backend.</p>
""",
    )
