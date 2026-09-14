#!/usr/bin/env python3
"""Generate the status icons from Material Design Icons paths.

Connect IQ renders no emoji, and hand-drawing recognisable glyphs with
primitives at ~36 px doesn't hold up. So these are real MDI paths rasterised
with cairosvg. One colour baked per file — the app just picks the right one.

    /path/to/backend/.venv/bin/python watch/resources/drawables/make_icons.py

(needs cairosvg — `pip install cairosvg`; the backend venv already has it.)

Icon language, per the 2026-09-04 design decision:
  * service reminder  -> wrench, amber   (maintenance, not a fault)
  * real fault        -> alert triangle, RED   (reserved; not wired yet)
  * red is exclusive to the triangle so the two never read the same
"""

from __future__ import annotations

from pathlib import Path

import cairosvg

HERE = Path(__file__).parent
PX = 44  # on-screen target ~36; a little headroom

GREY = "#96A6C2"
AMBER = "#F2B24A"
RED = "#F06060"
BLUE = "#5E94FF"
GREEN = "#8FD18F"

# MDI 24x24 path data (@mdi/js)
MDI = {
    "lock": "M12,17A2,2 0 0,0 14,15C14,13.89 13.1,13 12,13A2,2 0 0,0 10,15A2,2 0 0,0 12,17M18,8A2,2 0 0,1 20,10V20A2,2 0 0,1 18,22H6A2,2 0 0,1 4,20V10C4,8.89 4.9,8 6,8H7V6A5,5 0 0,1 12,1A5,5 0 0,1 17,6V8H18M12,3A3,3 0 0,0 9,6V8H15V6A3,3 0 0,0 12,3Z",
    "lock_open": "M18,8A2,2 0 0,1 20,10V20A2,2 0 0,1 18,22H6A2,2 0 0,1 4,20V10A2,2 0 0,1 6,8H15V6A3,3 0 0,0 9,6H7A5,5 0 0,1 17,6V8H18M12,17A2,2 0 0,0 14,15A2,2 0 0,0 12,13A2,2 0 0,0 10,15A2,2 0 0,0 12,17Z",
    "wrench": "M22.7,19L13.6,9.9C14.5,7.6 14,4.9 12.1,3C10.1,1 7.1,0.6 4.7,1.7L9,6L6,9L1.6,4.7C0.4,7.1 0.9,10.1 2.9,12.1C4.8,14 7.5,14.5 9.8,13.6L18.9,22.7C19.3,23.1 19.9,23.1 20.3,22.7L22.6,20.4C23.1,20 23.1,19.3 22.7,19Z",
    "alert": "M13,14H11V10H13M13,18H11V16H13M1,21H23L12,2L1,21Z",
    "flash": "M7,2V13H10V22L17,10H13L17,2H7Z",
    "wiper_wash": "M13,6C13,5.7 13.1,4.6 13.8,3.8L12,2.4L10.2,3.9C10.9,4.6 11,5.7 11,6C4.7,6.4 2,11 2,11L9,18C9,18 9.7,16.7 11,16.2V18.3C10.4,18.6 10,19.3 10,20A2,2 0 0,0 12,22A2,2 0 0,0 14,20C14,19.3 13.6,18.6 13,18.3V16.2C14.3,16.7 15,18 15,18L22,11C22,11 19.3,6.5 13,6M11,14.1C10.2,14.3 9.5,14.6 8.9,15.1L4.7,10.9C5.8,9.8 7.8,8.3 11,8.1V14.1M15.1,15.1C14.5,14.7 13.8,14.3 13,14.1V8.1C16.2,8.4 18.2,9.8 19.3,10.9L15.1,15.1M18,1.3L17.3,3.2C16.6,2.9 15.5,2.9 14.7,3.2L14,1.3C15.2,0.9 16.8,0.9 18,1.3M21,6H19C19,6 19,4.7 18.2,3.9L19.7,2.6C21,4 21,5.9 21,6M4.2,2.6L5.7,3.9C5,4.7 5,6 5,6H3C3,5.9 3,4 4.2,2.6M10,1.3L9.3,3.2C8.6,2.9 7.5,2.9 6.7,3.2L6,1.3C7.2,0.9 8.8,0.9 10,1.3Z",
    "tyre_alert": "M11,13H13V15H11V13M11,5H13V11H11V5M17,4.76C18.86,6.19 20,8.61 20,11C20,14 18.33,16.64 15.86,18H8.14C5.67,16.64 4,14 4,11C4,8.61 5.09,6.17 7,4.76V2H5V3.86C3.15,5.68 2,8.2 2,11C2,13.8 3.15,16.32 5,18.14V22H7V20H9V22H11V20H13V22H15V20H17V22H19V18.14C20.85,16.32 22,13.8 22,11C22,8.2 20.85,5.68 19,3.86V2H17V4.76Z",
    "steering": "M13,19.92C14.8,19.7 16.35,18.95 17.65,17.65C18.95,16.35 19.7,14.8 19.92,13H16.92C16.7,14 16.24,14.84 15.54,15.54C14.84,16.24 14,16.7 13,16.92V19.92M10,8H14L17,11H19.92C19.67,9.05 18.79,7.38 17.27,6C15.76,4.66 14,4 12,4C10,4 8.24,4.66 6.73,6C5.21,7.38 4.33,9.05 4.08,11H7L10,8M11,19.92V16.92C10,16.7 9.16,16.24 8.46,15.54C7.76,14.84 7.3,14 7.08,13H4.08C4.3,14.77 5.05,16.3 6.35,17.6C7.65,18.9 9.2,19.67 11,19.92M12,2C14.75,2 17.1,3 19.05,4.95C21,6.9 22,9.25 22,12C22,14.75 21,17.1 19.05,19.05C17.1,21 14.75,22 12,22C9.25,22 6.9,21 4.95,19.05C3,17.1 2,14.75 2,12C2,9.25 3,6.9 4.95,4.95C6.9,3 9.25,2 12,2Z",
}


def render(name: str, path: str, colour: str, scale: float = 1.0) -> None:
    """`scale` compensates for MDI glyphs that carry more internal padding —
    the padlock paths sit inside ~x:4-20, the wrench fills ~1-23."""
    px = round(PX * scale)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        f'<path d="{path}" fill="{colour}"/></svg>'
    )
    cairosvg.svg2png(
        bytestring=svg.encode(), write_to=str(HERE / f"{name}.png"),
        output_width=px, output_height=px,
    )
    print(f"  {name}.png  ({px}px)")


def main() -> None:
    render("icon_lock_closed", MDI["lock"], GREY, scale=1.18)
    render("icon_lock_open", MDI["lock_open"], AMBER, scale=1.18)
    render("icon_service", MDI["wrench"], AMBER)
    render("icon_washer", MDI["wiper_wash"], AMBER)       # washer fluid low
    render("icon_tyre", MDI["tyre_alert"], AMBER)         # tyre pressure warning
    render("icon_fault", MDI["alert"], RED, scale=1.12)   # reserved for real faults
    render("icon_in_use", MDI["steering"], BLUE)           # car reachable=false, CAR_IN_USE
    # Charging page: bolt always shown, coloured by state rather than
    # present/absent (distinct from the status-row bolt above).
    render("icon_bolt_green", MDI["flash"], GREEN, scale=1.1)
    render("icon_bolt_red", MDI["flash"], RED, scale=1.1)


if __name__ == "__main__":
    main()
