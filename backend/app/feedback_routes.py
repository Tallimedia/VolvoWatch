"""www.tallimedia.com's #contact form — relays a short message by email.

Not scoped to VolvoWatch; this is a general Tallimedia contact point that
happens to be hosted on this backend since it's the only server the site has.
"""

from __future__ import annotations

import asyncio
import email.utils
import logging
import smtplib
from email.message import EmailMessage

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from . import ratelimit
from .config import get_settings

router = APIRouter(tags=["feedback"])

_log = logging.getLogger(__name__)

_MAX_ATTEMPTS = 5
_WINDOW_S = 3600.0


class FeedbackRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    name: str = Field(default="", max_length=100)
    email: EmailStr | None = None
    # Honeypot: real visitors never see or fill this field (hidden in CSS).
    # A filled value means a bot — accept it silently, just don't send it.
    hp: str = Field(default="", max_length=200)


def _client_ip(request: Request) -> str:
    # Behind Cloudflare's proxy — request.client.host would just be the
    # tunnel/Traefik hop, not the real client.
    return request.headers.get("cf-connecting-ip") or (
        request.client.host if request.client else "unknown"
    )


def _send(body: FeedbackRequest) -> None:
    settings = get_settings()
    msg = EmailMessage()
    msg["Subject"] = "Tallimedia site feedback"
    msg["From"] = settings.smtp_from or settings.smtp_username
    msg["To"] = settings.feedback_to_email
    if body.email:
        msg["Reply-To"] = body.email
    msg["Date"] = email.utils.formatdate(localtime=True)
    sender_line = body.name or (body.email or "anonymous")
    msg.set_content(f"From: {sender_line}\n\n{body.message}")

    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)


@router.post("/feedback")
async def feedback(body: FeedbackRequest, request: Request) -> dict:
    settings = get_settings()
    if not settings.smtp_host:
        raise HTTPException(503, "feedback isn't configured on this deployment")

    if not ratelimit.allow(
        f"feedback:{_client_ip(request)}", max_attempts=_MAX_ATTEMPTS, window_s=_WINDOW_S
    ):
        raise HTTPException(429, "too many messages — try again later")

    if body.hp:
        return {"ok": True}

    try:
        await asyncio.to_thread(_send, body)
    except (OSError, smtplib.SMTPException) as exc:
        _log.warning("feedback email failed to send: %s", exc)
        raise HTTPException(502, "could not send — try again shortly") from exc

    return {"ok": True}
