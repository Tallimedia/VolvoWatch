"""Terms of Service + Privacy Policy pages.

Referenced from the Volvo API application registration and shown on the OAuth
consent screen. Single source of truth for both pages' content — the static
site's volvowatch/terms.html is a design reference only, not served live
(see html/site/README.md).
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .webshell import page

router = APIRouter(tags=["legal"])

_CONTACT = "iot@tallimedia.com"
_EFFECTIVE = "2026-09-13"

_MAIN_STYLE = (
    "max-width: 980px; margin: 0 auto; padding: 48px 32px 24px; "
    "display: grid; grid-template-columns: 220px minmax(0, 1fr); "
    "gap: 48px; align-items: start"
)


def _section(number: str, anchor: str, title: str, body: str) -> str:
    return (
        f'<section id="{anchor}">'
        f'<div style="display: flex; align-items: baseline; gap: 14px; margin-bottom: 12px">'
        f'<span style="font-family: var(--font-heading); font-size: 13px; '
        f'letter-spacing: 0.08em; text-transform: uppercase; '
        f'color: var(--color-accent-700)">{number}</span>'
        f'<h2 style="font-size: 30px; margin: 0">{title}</h2></div>'
        f'<p style="font-size: 17px; margin: 0; color: var(--color-neutral-900)">{body}</p>'
        f"</section>"
    )


def _sidebar(sections: list[tuple[str, str]]) -> str:
    links = "".join(
        f'<a href="#{anchor}" style="text-decoration: none; '
        f'color: var(--color-neutral-700)">{title}</a>'
        for anchor, title in sections
    )
    return (
        '<nav style="position: sticky; top: 24px; display: grid; gap: 8px; '
        "font-family: var(--font-heading); font-size: 14px; letter-spacing: 0.04em; "
        "text-transform: uppercase; border-left: 1px solid var(--color-divider); "
        f'padding-left: 16px">{links}</nav>'
    )


def _footer_card(right_link_href: str, right_link_text: str) -> str:
    return (
        '<div class="blueprint" style="padding: 24px; display: flex; '
        'justify-content: space-between; gap: 24px; flex-wrap: wrap; align-items: center">'
        "<div>"
        '<div style="font-family: var(--font-heading); font-size: 12px; '
        'letter-spacing: 0.08em; text-transform: uppercase; '
        f'color: var(--color-neutral-600)">Effective</div>'
        f'<div style="font-family: var(--font-heading); font-size: 22px">{_EFFECTIVE}</div>'
        "</div><div>"
        '<div style="font-family: var(--font-heading); font-size: 12px; '
        'letter-spacing: 0.08em; text-transform: uppercase; '
        f'color: var(--color-neutral-600)">Contact</div>'
        f'<a href="mailto:{_CONTACT}" style="font-family: var(--font-heading); '
        f'font-size: 22px; text-decoration: none">{_CONTACT}</a>'
        "</div>"
        f'<a class="btn btn-secondary" href="{right_link_href}" '
        f'style="text-transform: uppercase; letter-spacing: 0.06em">{right_link_text}</a>'
        '<i class="corner tl"></i><i class="corner tr"></i>'
        '<i class="corner bl"></i><i class="corner br"></i>'
        "</div>"
    )


def _hero(tag2: str, title: str, intro: str) -> str:
    return (
        '<header style="border-bottom: 1px solid var(--color-divider)">'
        '<div style="max-width: 980px; margin: 0 auto; padding: 64px 32px 40px">'
        '<div style="display: flex; gap: 8px; margin-bottom: 20px">'
        f'<span class="tag tag-accent">Effective {_EFFECTIVE}</span>'
        f'<span class="tag tag-outline">{tag2}</span></div>'
        f'<h1 style="font-size: 64px; line-height: 0.95; letter-spacing: -0.02em; '
        f'margin: 0 0 20px">{title}</h1>'
        f'<p style="font-size: 19px; color: var(--color-neutral-800); max-width: 62ch; '
        f'margin: 0; text-wrap: pretty">{intro}</p>'
        "</div></header>"
    )


def _footer_bar(back_href: str, back_text: str) -> str:
    return (
        '<footer style="border-top: 1px solid var(--color-divider); padding: 32px">'
        '<div style="max-width: 980px; margin: 0 auto; display: flex; gap: 24px; '
        "flex-wrap: wrap; justify-content: space-between; font-size: 13px; "
        'color: var(--color-neutral-600)">'
        "<span>An independent project, not affiliated with, endorsed by, or "
        "supported by Volvo Cars.</span>"
        f'<a href="{back_href}">← {back_text}</a>'
        "</div></footer>"
    )


@router.get("/terms", response_class=HTMLResponse)
async def terms() -> str:
    sections = [
        ("use", "Use of the app"),
        ("availability", "Service availability"),
        ("fees", "Fees"),
        ("warranty", "No warranty"),
        ("liability", "Limitation of liability"),
        ("changes", "Changes"),
    ]
    body = (
        _hero(
            "Non-commercial project",
            "VolvoWatch —<br>Terms of Service",
            "VolvoWatch is an independent, non-commercial hobby project that shows "
            "your Volvo vehicle information on a Garmin watch and lets you send a "
            "limited set of remote commands (such as starting climatisation). It is "
            "<strong>not affiliated with, endorsed by, or supported by Volvo Cars</strong>. "
            '"Volvo" is a trademark of Volvo Trademark Holding AB. VolvoWatch is '
            "built on the public Volvo Cars Developer API.",
        )
        + f'<div style="{_MAIN_STYLE}">'
        + _sidebar(sections)
        + '<div style="display: grid; gap: 36px">'
        + _section(
            "01",
            "use",
            "Use of the app",
            "You may use the app only with a Volvo vehicle you are authorised to "
            "access, and only by granting consent through your own Volvo ID, on "
            "Volvo's own sign-in page — this service never sees your Volvo password. "
            "You are responsible for anything done with your account through the "
            "app, including remote commands you trigger.",
        )
        + _section(
            "02",
            "availability",
            "Service availability",
            "This service is run on a best-effort basis, with <strong>no "
            "service-level agreement (SLA)</strong> — no guaranteed uptime, response "
            "time, or support commitment. It may be unavailable during maintenance, "
            "hosting-provider outages, or Volvo API issues outside our control, and "
            "it may be changed or discontinued at any time with reasonable notice.",
        )
        + _section(
            "03",
            "fees",
            "Fees",
            "VolvoWatch is currently free to use. That may change: a fee or "
            "subscription could be introduced for this service at any time, and "
            "doing so does not require asking existing users first. That said, "
            "<strong>nothing will ever be charged to you without your explicit "
            "acceptance</strong> at the time — no silent or automatic billing. If "
            "you don't accept a fee that's introduced later, your access may simply "
            "end rather than be charged for.",
        )
        + _section(
            "04",
            "warranty",
            "No warranty",
            'The app is provided "as is", with no warranty of any kind. Vehicle '
            "data may be delayed, incomplete, or unavailable, and commands may fail "
            "or be delayed. Do not rely on the app for anything safety-critical. "
            "The app depends on the Volvo Cars API and may stop working if that API "
            "changes or access is withdrawn.",
        )
        + _section(
            "05",
            "liability",
            "Limitation of liability",
            "To the maximum extent permitted by law, the operator of the app is "
            "not liable for any loss or damage arising from use of, or inability "
            "to use, the app.",
        )
        + _section(
            "06",
            "changes",
            "Changes",
            "These terms may change. Continued use after a change means you "
            "accept the updated terms.",
        )
        + _footer_card("/privacy", "Privacy policy")
        + "</div></div>"
        + _footer_bar("/", "Back to VolvoWatch")
    )
    return page("Terms of Service — VolvoWatch", body, crumb="Terms", main_style="display:contents")


@router.get("/privacy", response_class=HTMLResponse)
async def privacy() -> str:
    sections = [
        ("stored", "What is stored"),
        ("location", "Where it is stored"),
        ("deleting", "Deleting your data"),
        ("third-parties", "Third parties"),
    ]
    body = (
        _hero(
            "Privacy",
            "VolvoWatch —<br>Privacy Policy",
            "This policy explains what the app stores and why. It is run by "
            "Tallimedia, not a large company — the same operator as the rest of "
            "the backend.",
        )
        + f'<div style="{_MAIN_STYLE}">'
        + _sidebar(sections)
        + '<div style="display: grid; gap: 36px">'
        + _section(
            "01",
            "stored",
            "What is stored",
            "<b>Volvo OAuth tokens</b> — an access token and a refresh token for "
            "your Volvo ID, so the app can read your vehicle data and send commands "
            "without asking you to sign in every time. The refresh token is "
            "encrypted at rest. <b>Your VIN</b> and a Volvo account identifier, to "
            "know which vehicle to query. <b>A device token</b> for each Garmin "
            "watch you pair, stored only as a hash. <b>A short-lived cache</b> "
            "(about one minute) of the vehicle status last fetched from Volvo. "
            "Vehicle data (fuel, battery, range, lock state, service intervals and, "
            "if enabled later, location) passes through the backend to your watch. "
            "It is not sold, shared, or used for any purpose other than serving it "
            "to your own paired devices.",
        )
        + _section(
            "02",
            "location",
            "Where it is stored",
            "On infrastructure operated by Tallimedia. No third-party analytics or "
            "advertising services are used.",
        )
        + _section(
            "03",
            "deleting",
            "Deleting your data",
            "You can revoke the app's access at any time from your Volvo ID "
            "account settings. To have stored tokens and identifiers deleted from "
            "the backend, contact the address below.",
        )
        + _section(
            "04",
            "third-parties",
            "Third parties",
            "The app communicates with the Volvo Cars API (subject to Volvo's own "
            "terms and privacy policy) and with Garmin's Connect IQ platform, which "
            "relays requests between your watch and the backend.",
        )
        + _footer_card("/terms", "Terms of Service")
        + "</div></div>"
        + _footer_bar("/", "Back to VolvoWatch")
    )
    return page("Privacy Policy — VolvoWatch", body, crumb="Privacy", main_style="display:contents")
