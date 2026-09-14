"""Shared HTML shell for every browser-facing page (auth_routes.py,
legal_routes.py) — same design system as the static marketing site
(../html/site/styles.css, mirrored into app/static/), so a server-rendered
page doesn't visually drift from it. One implementation, not copy-pasted
per route module.
"""

from __future__ import annotations

_TALLIMEDIA_URL = "https://www.tallimedia.com"


def nav(crumb: str = "") -> str:
    """The Tallimedia / VolvoWatch [/ <crumb>] breadcrumb used on every page."""
    crumb_html = (
        f'<span style="color: var(--color-neutral-400)">/</span>'
        f'<span style="font-family: var(--font-heading); font-weight: 600; '
        f'font-size: 17px; color: var(--color-neutral-700)">{crumb}</span>'
        if crumb
        else ""
    )
    return f"""<nav style="display: flex; align-items: center; gap: 24px; padding: 14px 32px; border-bottom: 1px solid var(--color-divider); flex-wrap: wrap">
    <a href="{_TALLIMEDIA_URL}" style="display: flex; align-items: center; gap: 10px; text-decoration: none; color: var(--color-text)">
      <svg width="22" height="22" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="5">
        <path d="M8 27 32 9l24 18"></path>
        <path d="M14 27v29h36V27"></path>
        <path d="M32 56V41" stroke="var(--color-accent)"></path>
      </svg>
      <span style="font-family: var(--font-heading); font-weight: 600; font-size: 17px; letter-spacing: 0.06em; text-transform: uppercase">Tallimedia</span>
    </a>
    <span style="color: var(--color-neutral-400)">/</span>
    <a href="/" style="display: flex; align-items: center; gap: 8px; font-family: var(--font-heading); font-weight: 600; font-size: 17px; text-decoration: none; color: var(--color-text)">
      <svg width="20" height="20" viewBox="0 0 64 64" fill="none">
        <circle cx="32" cy="32" r="21" stroke="var(--color-accent-900)" stroke-width="5"></circle>
        <path d="M11 32a21 21 0 0 1 42 0" stroke="var(--color-accent)" stroke-width="5"></path>
        <path d="M32 15 V32 L45 39" stroke="var(--color-accent-900)" stroke-width="6" stroke-linecap="square"></path>
      </svg>
      VolvoWatch
    </a>
    {crumb_html}
  </nav>"""


def page(title: str, body: str, *, crumb: str = "", main_style: str = "") -> str:
    """Full HTML document: static-site styles.css, the breadcrumb nav, and
    `body` inside a centered <main>. `main_style` overrides the default
    centered-narrow-column layout for pages that need something wider
    (e.g. the terms page's sidebar + section layout)."""
    main = main_style or "max-width: 30rem; margin: 0 auto; padding: 48px 32px"
    return f"""<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="/static/styles.css">
<style>
 body{{margin:0}}
 a{{color:var(--color-accent-700)}}
 a:hover{{color:var(--color-accent-900)}}
</style>
<div style="background: var(--color-bg); color: var(--color-text); font-family: var(--font-body); font-size: 15px; line-height: 1.55; min-height: 100vh">
{nav(crumb)}
<main style="{main}">{body}</main>
</div>"""
