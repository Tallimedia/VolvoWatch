# Tallimedia static site

Plain static HTML. No build step, no JS.

    site/
      index.html              design source for www.tallimedia.com
      styles.css               Industry design-system tokens + components (the only stylesheet)
      assets/                  screenshots used by index.html
      fonts/                   self-hosted Barlow / Barlow Condensed .woff2
      volvowatch/
        index.html             design source for volvowatchapp.tallimedia.com's "/"
        terms.html              design reference only — see below
        styles.css, fonts/, assets/   own copies, so this folder is self-contained

## What's actually deployed where

- `index.html` (this folder, minus `volvowatch/`) is deployed as-is to
  `www.tallimedia.com`, via a plain `nginx:alpine` container on `public-vm`.
- `volvowatch/index.html` is **mirrored into `backend/app/landing/`** and
  shipped inside the backend's Docker image — that copy, not this one, is
  what's actually live at `volvowatchapp.tallimedia.com/`. Keep the two in
  sync by hand (there's no build step); `backend/app/main.py` mounts
  `app/landing/` at `"/"`, after every other route.
- `volvowatch/terms.html` is a **design reference only, not served live** —
  the real `/terms` and `/privacy` are rendered by
  `backend/app/legal_routes.py`. Port styling changes there.
- Fonts are self-hosted (`fonts/*.woff2`, `@font-face` in `styles.css`) — no
  Google Fonts calls at runtime.

## Design spec, for whoever builds the next asset

Trimmed off the live `volvowatch/index.html` on 2026-09-14 (it was showing
internal design-review content to real visitors) but kept here as reference:

- **Favicon**: 48 / 32 / 16 px, dark accent background, white ring-and-hand
  mark (same needle-and-arc motif as the VolvoWatch logo).
- **App store header image**: 1440 × 720, dark accent background, headline +
  subhead on the left, a status-page capture in a circular crop on the right.
- **Logo lockups**: Tallimedia = stable gable + drive-in-the-bay mark,
  horizontal wordmark. VolvoWatch = needle + arc mark, horizontal wordmark.
  Both are inline SVG in the pages themselves — no image files needed.

## Other notes

- The Monday.com contact-form iframe
  (`forms.monday.com/forms/embed/cc1320e6ed685d7e3e1a12d8be24f451?r=euc1`)
  lives on `volvowatch/index.html`'s own Contact section, not on the main
  `index.html` — it's VolvoWatch-specific feedback, and the main site is
  meant to host more than one app over time.
- Cross-links between the two sites use full `https://` URLs (they're
  separate subdomains, not folders under one origin).
