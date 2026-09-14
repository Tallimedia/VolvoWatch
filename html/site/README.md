# Tallimedia static site

Plain static HTML. No build step, no JS. Serve the `site/` folder as-is.

    site/
      index.html              tallimedia.com
      styles.css              Industry design-system tokens + components (the only stylesheet)
      assets/                 watch captures used by the pages
      volvowatch/
        index.html            volvowatchapp.tallimedia.com (product landing)
        terms.html            /terms

## Notes for deployment

- Fonts load from Google Fonts (Barlow, Barlow Condensed). Self-host them if you
  would rather not call out.
- `volvowatch/index.html` contains a *mock* of the pairing-result page inside the
  setup section (masked VIN `XXXXXXXXXXXXXXXXX`, code `123456`). The real page is
  rendered by the backend in `backend/app/auth_routes.py` — port the styling there,
  do not serve this mock as the live callback page.
- `volvowatch/terms.html` duplicates the text served by `backend/app/legal_routes.py`.
  Pick one source of truth; if the backend keeps serving /terms, this file is the
  design reference for restyling it.
- The Monday contact form on `index.html` is an iframe to
  `forms.monday.com/forms/embed/cc1320e6ed685d7e3e1a12d8be24f451?r=euc1`. Verify it
  frames on your domain; the "open in new tab" link is the fallback.
- Internal links assume the two sites sit at `/` and `/volvowatch/`. If VolvoWatch
  gets its own subdomain, change the cross-links in both files.
- Logos are inline SVG (Tallimedia: stable gable + drive in the bay; VolvoWatch:
  needle + arc). No image files needed. Favicons are not wired up yet.
