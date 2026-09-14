#!/usr/bin/env python3
"""Render the Connect IQ Store artwork.

  hero-1440x720.png    banner
  cover-500x500.png    square tile

Both draw the watch screen the way the app actually renders it, so the artwork
can't drift from the product. No Volvo branding or logos — this is an
unaffiliated project.

    python3 watch/store/make_store_art.py
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
HERO = HERE / "hero-1440x720.png"
COVER = HERE / "cover-500x500.png"

# Palette — dark, matching the app's own screen.
BG_TOP = (9, 13, 26)
BG_BOTTOM = (19, 26, 48)
WHITE = (245, 248, 253)
GREY = (150, 166, 194)
DIM = (98, 112, 138)
ACCENT = (94, 148, 255)
AMBER = (242, 178, 74)
RED = (240, 96, 96)

ICON_DIR = Path(__file__).resolve().parents[1] / "resources" / "drawables"
BEZEL_OUT = (62, 68, 82)
BEZEL_IN = (28, 32, 44)
SCREEN = (0, 0, 0)

# The real fenix847mm device skin the Connect IQ simulator itself renders
# (case, buttons, GARMIN text, strap stubs) — not ours to redistribute, so it's
# read straight from the installed SDK rather than copied into the repo.
# Screen rect is straight from that device's own simulator.json.
DEVICE_SKIN_PATH = (
    Path.home() / "Library/Application Support/Garmin/ConnectIQ/Devices"
    / "fenix847mm" / "fenix847mm.png"
)
SCREEN_RECT = (134, 221, 454, 454)  # x, y, w, h


def device_skin() -> Image.Image | None:
    """The real device-skin PNG, or None if the SDK isn't installed here —
    callers fall back to the hand-drawn ring so the script still runs."""
    if not DEVICE_SKIN_PATH.exists():
        return None
    return Image.open(DEVICE_SKIN_PATH).convert("RGBA")


_cutout_cache: Image.Image | None = None


def skin_cutout() -> Image.Image | None:
    """The device skin with its flat white background stripped to
    transparent, so just the case/buttons/strap survive — for compositing
    onto the hero/cover art's own dark gradient instead of a white box.
    Global threshold rather than flood-fill from the corners: a couple of
    background slivers at the strap/case hinge aren't corner-connected, and
    nothing on the actual case gets anywhere near pure white."""
    global _cutout_cache
    if _cutout_cache is not None:
        return _cutout_cache
    skin = device_skin()
    if skin is None:
        return None
    arr = np.array(skin)
    near_white = (arr[:, :, :3] >= 250).all(axis=2) & (arr[:, :, 3] == 255)
    arr[near_white, 3] = 0
    _cutout_cache = Image.fromarray(arr)
    return _cutout_cache

SF = "/System/Library/Fonts/SFNS.ttf"
HELV = "/System/Library/Fonts/HelveticaNeue.ttc"


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    """SF with a variation axis where possible, Helvetica Neue otherwise."""
    try:
        f = ImageFont.truetype(SF, size)
        try:
            f.set_variation_by_name("Bold" if weight == "bold" else "Regular")
        except Exception:
            pass
        return f
    except Exception:
        return ImageFont.truetype(HELV, size)


def vertical_gradient(size: tuple[int, int], top, bottom) -> Image.Image:
    w, h = size
    grad = Image.new("RGB", (1, h))
    px = grad.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return grad.resize((w, h))


def centered(draw, cx, cy, text, fnt, fill):
    """Draw text centred on (cx, cy) using its real ink box."""
    l, t, r, b = draw.textbbox((0, 0), text, font=fnt)
    draw.text((cx - (r + l) / 2, cy - (b + t) / 2), text, font=fnt, fill=fill)


def bezel_only(d: int) -> Image.Image:
    """The watch ring + tick marks, transparent centre — for framing a real
    screen capture. Returns a d x d RGBA image with the screen area clear."""
    ss = 4
    size = d * ss
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.ellipse([0, 0, size - 1, size - 1], fill=BEZEL_OUT + (255,))
    inset = int(size * 0.035)
    ld.ellipse([inset, inset, size - inset, size - inset], fill=BEZEL_IN + (255,))
    bez = int(size * 0.075)
    ld.ellipse([bez, bez, size - bez, size - bez], fill=(0, 0, 0, 0))  # clear screen hole
    r_out, r_in = size / 2 - inset * 0.55, size / 2 - bez * 0.92
    for i in range(60):
        a = math.radians(i * 6 - 90)
        w = 3 * ss if i % 5 else 6 * ss
        ld.line(
            [(size / 2 + r_in * math.cos(a), size / 2 + r_in * math.sin(a)),
             (size / 2 + r_out * math.cos(a), size / 2 + r_out * math.sin(a))],
            fill=(96, 104, 120, 255), width=w,
        )
    return layer.resize((d, d), Image.LANCZOS)


STORE_MAX_BYTES = 150_000  # Connect IQ store caps screenshots at 150 kB


def _save_under_cap(img: Image.Image, out: Path, cap: int = STORE_MAX_BYTES) -> None:
    """Save a PNG under `cap` bytes. The art is mostly flat dark fill + text, so
    an adaptive palette costs nothing visible and roughly halves the file.

    FASTOCTREE, not MEDIANCUT — MEDIANCUT picks palette entries by splitting
    the color *population*, so a small saturated region (green charging
    text/icons against a large grey/navy device photo) gets merged into the
    dominant neutral cluster and reads as grey. FASTOCTREE partitions the
    actual color *space* instead, so a distinct hue keeps its own entry even
    at a small pixel count — confirmed empirically: same 128-color budget,
    MEDIANCUT turned Theme.OK green text to (182,195,182); FASTOCTREE kept
    it green, in a file less than half the size besides."""
    rgb = img.convert("RGB")
    rgb.save(out, "PNG", optimize=True)
    if out.stat().st_size <= cap:
        return
    for colours in (256, 192, 128, 96, 64):
        rgb.quantize(colors=colours, method=Image.FASTOCTREE, dither=Image.Dither.NONE).save(
            out, "PNG", optimize=True
        )
        if out.stat().st_size <= cap:
            return


GREEN = (143, 209, 143)  # Theme.OK — matches the "charging" green elsewhere


def _synthetic_glance_screen(d: int) -> Image.Image:
    """The glance-carousel list row, hand-composited rather than framed from
    a raw sim capture — GlanceView.onUpdate() only draws the *content*
    inside that row (see source/GlanceView.mc), the highlighted bar and app
    icon around it are the system's own glance-list chrome, which a plain
    'File -> Save Screen Capture' of the standalone glance canvas doesn't
    include. Mirrors the real row layout: launcher icon, car name, then
    battery (green while charging, matching MainView/ChargingView) + fuel."""
    ss = 4
    size = d * ss
    img = Image.new("RGBA", (size, size), SCREEN + (255,))
    dr = ImageDraw.Draw(img)

    bar_l, bar_r = int(size * 0.11), int(size * 0.89)
    bar_t, bar_b = int(size * 0.40), int(size * 0.63)
    dr.rectangle([bar_l, bar_t, bar_r, bar_b], fill=(22, 27, 42, 255))
    stripe_w = max(int(size * 0.006), 2 * ss)
    dr.rectangle([bar_l, bar_t, bar_l + stripe_w, bar_b], fill=ACCENT + (255,))

    icon_d = int(size * 0.10)
    icon = Image.open(ICON_DIR / "launcher_icon.png").convert("RGBA").resize(
        (icon_d, icon_d), Image.LANCZOS
    )
    icon_x = bar_l + int(size * 0.045)
    icon_y = (bar_t + bar_b) // 2 - icon_d // 2
    img.alpha_composite(icon, (icon_x, icon_y))

    text_x = icon_x + icon_d + int(size * 0.035)
    name_f = font(int(size * 0.052))
    stat_f = font(int(size * 0.058))
    l, t, r, b = dr.textbbox((0, 0), "My XC60", font=name_f)
    dr.text((text_x, bar_t + int(size * 0.045) - t), "My XC60", font=name_f, fill=WHITE)

    batt, fuel, gap = "Bat 6%", "Fuel 48%", "   "
    bw = dr.textlength(batt, font=stat_f)
    gw = dr.textlength(gap, font=stat_f)
    _, st, _, sb = dr.textbbox((0, 0), batt, font=stat_f)
    stat_y = bar_b - int(size * 0.05) - sb
    dr.text((text_x, stat_y), batt, font=stat_f, fill=GREEN)
    dr.text((text_x + bw + gw, stat_y), fuel, font=stat_f, fill=WHITE)

    return img.resize((d, d), Image.LANCZOS)


def make_glance_screenshot(out: Path) -> None:
    """Frame the synthetic glance-card render onto the real device skin,
    same compositing as frame_capture() but with hand-drawn content instead
    of a raw sim capture (see _synthetic_glance_screen)."""
    skin = device_skin()
    sx, sy, sw, sh = SCREEN_RECT
    screen = _synthetic_glance_screen(sw)

    if skin is not None:
        canvas = skin.copy()
        mask = Image.new("L", (sw, sh), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, sw - 1, sh - 1], fill=255)
        canvas.paste(screen, (sx, sy), mask)
        _save_under_cap(canvas, out)
        print(f"{out.name}  {canvas.size[0]}x{canvas.size[1]}  {out.stat().st_size:,} bytes")
        return

    size = 720
    canvas = vertical_gradient((size, size), BG_TOP, BG_BOTTOM).convert("RGBA")
    d = int(size * 0.92)
    screen_d = int(d * (1 - 2 * 0.075))
    disc = _synthetic_glance_screen(screen_d)
    mask = Image.new("L", (screen_d, screen_d), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, screen_d - 1, screen_d - 1], fill=255)
    cx = cy = size // 2
    canvas.paste(disc, (cx - screen_d // 2, cy - screen_d // 2), mask)
    canvas.alpha_composite(bezel_only(d), (cx - d // 2, cy - d // 2))
    _save_under_cap(canvas, out)
    print(f"{out.name}  {size}x{size}  {out.stat().st_size:,} bytes")


def frame_capture(src: Path, out: Path, size: int = 720) -> None:
    """Composite a 454x454 sim capture into an actual watch.

    The store does not add a device frame to uploaded images, so a bare capture
    shows as a flat black square. Prefers the real fenix847mm device skin (the
    same image the Connect IQ simulator itself renders) so the screenshot reads
    as a photo of the real device; falls back to a hand-drawn ring if the SDK
    isn't installed on whatever machine runs this.
    """
    shot = Image.open(src).convert("RGBA")
    skin = device_skin()

    if skin is not None:
        canvas = skin.copy()
        sx, sy, sw, sh = SCREEN_RECT
        disc = shot.resize((sw, sh), Image.LANCZOS)
        mask = Image.new("L", (sw, sh), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, sw - 1, sh - 1], fill=255)
        canvas.paste(disc, (sx, sy), mask)
        _save_under_cap(canvas, out)
        print(f"{out.name}  {canvas.size[0]}x{canvas.size[1]}  {out.stat().st_size:,} bytes")
        return

    canvas = vertical_gradient((size, size), BG_TOP, BG_BOTTOM).convert("RGBA")
    d = int(size * 0.92)
    # the round screen sits inside the ~7.5% bezel
    screen_d = int(d * (1 - 2 * 0.075))
    disc = shot.resize((screen_d, screen_d), Image.LANCZOS)
    # circular mask so the square capture reads as a round watch face
    mask = Image.new("L", (screen_d, screen_d), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, screen_d - 1, screen_d - 1], fill=255)
    cx = cy = size // 2
    canvas.paste(disc, (cx - screen_d // 2, cy - screen_d // 2), mask)
    canvas.alpha_composite(bezel_only(d), (cx - d // 2, cy - d // 2))

    _save_under_cap(canvas, out)
    print(f"{out.name}  {size}x{size}  {out.stat().st_size:,} bytes")


def _synthetic_screen(d: int, *, compact: bool = False) -> Image.Image:
    """The status screen's own content (mirroring MainView.drawStatus),
    rendered standalone on a black square — no bezel. `d` is the screen
    diameter; content is proportioned exactly as draw_watch used to draw it
    straight onto the bezel image. `compact` drops the two smallest lines,
    which turn to mush at tile sizes."""
    ss = 4  # supersample for clean text/icons
    size = d * ss
    img = Image.new("RGBA", (size, size), SCREEN + (255,))
    dr = ImageDraw.Draw(img)
    sx, sy = size // 2, 0
    s = size

    if compact:
        centered(dr, sx, sy + s * 0.245, "My XC60", font(int(s * 0.072)), GREY)
        centered(dr, sx, sy + s * 0.44, "272", font(int(s * 0.275), "bold"), WHITE)
        centered(dr, sx, sy + s * 0.59, "km tot range", font(int(s * 0.068)), GREY)
        _batt_fuel(dr, sx, sy + s * 0.74, int(s * 0.088), 7)
        return img.resize((d, d), Image.LANCZOS)

    centered(dr, sx, sy + s * 0.235, "My XC60", font(int(s * 0.062)), GREY)
    centered(dr, sx, sy + s * 0.375, "272", font(int(s * 0.225), "bold"), WHITE)
    centered(dr, sx, sy + s * 0.50, "km tot range", font(int(s * 0.055)), GREY)
    _batt_fuel(dr, sx, sy + s * 0.605, int(s * 0.082), 7)
    _icon_row(img, sx, int(sy + s * 0.715), int(s * 0.10),
              ["icon_lock_closed.png", "icon_service.png", "icon_bolt_green.png"])
    centered(dr, sx, sy + s * 0.815, "82 350 km", font(int(s * 0.052)), GREY)
    centered(dr, sx, sy + s * 0.885, "Updated just now", font(int(s * 0.048)), DIM)
    return img.resize((d, d), Image.LANCZOS)


def draw_watch(img: Image.Image, cx: int, cy: int, d: int, *, compact: bool = False) -> None:
    """A round watch, screen showing the real status layout, at (cx, cy) with
    bezel diameter `d`. Composites onto the real device skin (case, buttons,
    strap stubs) when the Connect IQ SDK is installed; falls back to a
    hand-drawn ring + tick marks otherwise."""
    screen_d = int(d * 0.85)
    screen = _synthetic_screen(screen_d, compact=compact)
    cutout = skin_cutout()

    if cutout is not None:
        sx, sy, sw, sh = SCREEN_RECT
        k = screen_d / sw
        w, h = cutout.size
        watch = cutout.resize((round(w * k), round(h * k)), Image.LANCZOS)
        rx, ry, rw, rh = sx * k, sy * k, sw * k, sh * k
        mask = Image.new("L", (round(rw), round(rh)), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, round(rw) - 1, round(rh) - 1], fill=255)
        watch.paste(screen.resize((round(rw), round(rh)), Image.LANCZOS), (round(rx), round(ry)), mask)
        center = (round(rx + rw / 2), round(ry + rh / 2))
        paste_at = (cx - center[0], cy - center[1])
        img.paste(watch, paste_at, watch) if img.mode == "RGBA" else img.paste(
            watch.convert("RGB"), paste_at, watch.split()[-1]
        )
        return

    ss = 4  # supersample for clean circles
    size = d * ss
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)

    # bezel rings
    ld.ellipse([0, 0, size - 1, size - 1], fill=BEZEL_OUT + (255,))
    inset = int(size * 0.035)
    ld.ellipse([inset, inset, size - inset, size - inset], fill=BEZEL_IN + (255,))
    bez = int(size * 0.075)
    ld.ellipse([bez, bez, size - bez, size - bez], fill=SCREEN + (255,))

    # tick marks around the bezel
    r_out, r_in = size / 2 - inset * 0.55, size / 2 - bez * 0.92
    for i in range(60):
        a = math.radians(i * 6 - 90)
        w = 3 * ss if i % 5 else 6 * ss
        ld.line(
            [
                (size / 2 + r_in * math.cos(a), size / 2 + r_in * math.sin(a)),
                (size / 2 + r_out * math.cos(a), size / 2 + r_out * math.sin(a)),
            ],
            fill=(96, 104, 120, 255),
            width=w,
        )

    layer = layer.resize((d, d), Image.LANCZOS)
    img.paste(layer, (cx - d // 2, cy - d // 2), layer)

    sx, sy = cx, cy - d // 2
    mask = Image.new("L", screen.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, screen.size[0] - 1, screen.size[1] - 1], fill=255)
    img.paste(screen, (sx - screen.size[0] // 2, sy), mask)


def _batt_fuel(dr, cx, cy, size, batt_pct):
    """'Bat X%    Fuel Y%' with the battery figure reddened when low."""
    batt = f"Bat {batt_pct}%"
    fuel = "Fuel 51%"
    gap = "    "
    f = font(size)
    bw = dr.textlength(batt, font=f)
    gw = dr.textlength(gap, font=f)
    fw = dr.textlength(fuel, font=f)
    total = bw + gw + fw
    x = cx - total / 2
    colour = RED if batt_pct < 8 else (AMBER if batt_pct < 15 else WHITE)
    _, t, _, b = dr.textbbox((0, 0), batt, font=f)
    y = cy - (b + t) / 2
    dr.text((x, y), batt, font=f, fill=colour)
    dr.text((x + bw + gw, y), fuel, font=f, fill=WHITE)


def _icon_row(img, cx, cy, size, files):
    step = int(size * 1.55)
    x = cx - (len(files) - 1) * step // 2
    for name in files:
        p = ICON_DIR / name
        if not p.exists():
            continue
        ic = Image.open(p).convert("RGBA").resize((size, size), Image.LANCZOS)
        img.paste(ic, (int(x - size / 2), int(cy - size / 2)), ic)
        x += step


def make_cover() -> None:
    """500x500 square tile. Legible at thumbnail size, so: fewer words."""
    S = 500
    img = vertical_gradient((S, S), BG_TOP, BG_BOTTOM)

    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(50, 0, -1):
        r = 150 + i * 3
        gd.ellipse([S // 2 - r, 232 - r, S // 2 + r, 232 + r], fill=(40, 74, 150, 4))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

    # d=234 keeps the whole device (straps included) at the same ~404px
    # vertical footprint the old bare-circle art used, so the caption below
    # still clears it.
    draw_watch(img, S // 2, 232, 234, compact=True)

    d = ImageDraw.Draw(img)
    centered(d, S // 2, 466, "My Volvo Watch App", font(27, "bold"), WHITE)

    img.save(COVER, "PNG")
    print(f"{COVER.name}  {img.size[0]}x{img.size[1]}  {COVER.stat().st_size:,} bytes")


def make_hero() -> None:
    W, H = 1440, 720
    img = vertical_gradient((W, H), BG_TOP, BG_BOTTOM)

    # soft accent glow behind the watch
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gx, gy = 1080, 360
    for i in range(60, 0, -1):
        r = 250 + i * 4
        gd.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(40, 74, 150, 3))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

    d = ImageDraw.Draw(img)

    # --- left column ---
    x = 96
    max_title_w = 660  # keep clear of the watch on the right

    title = "My Volvo Watch App"
    size = 74
    while size > 34:
        f = font(size, "bold")
        if d.textlength(title, font=f) <= max_title_w:
            break
        size -= 2
    d.text((x, 196), title, font=font(size, "bold"), fill=WHITE)

    d.text((x, 292), "Range, fuel and battery at a glance —", font=font(31), fill=GREY)
    d.text((x, 334), "and start the heating from your wrist.", font=font(31), fill=GREY)

    bullets = [
        "Combined petrol + electric range",
        "Lock, doors, service and tyre warnings",
        "Start / stop climatisation",
        "Odometer and trip details, one swipe away",
    ]
    by = 402
    for b in bullets:
        d.ellipse([x + 3, by + 11, x + 13, by + 21], fill=ACCENT)
        d.text((x + 32, by), b, font=font(27), fill=(206, 216, 232))
        by += 44

    d.text((x, 604), "Requires a self-hosted VolvoWatch backend.",
           font=font(21), fill=DIM)
    d.text((x, 634), "Independent project — not affiliated with Volvo Cars.",
           font=font(21), fill=DIM)

    # d=360 keeps the whole device (straps included) within the canvas height
    # and clear of the title/bullets on the left — bigger than the old bare
    # circle needed since the real skin's straps add real vertical extent.
    draw_watch(img, gx, gy, 360)

    img.save(HERO, "PNG")
    print(f"{HERO.name}  {img.size[0]}x{img.size[1]}  {HERO.stat().st_size:,} bytes")


if __name__ == "__main__":
    make_hero()
    make_cover()
    # frame any raw sim captures named capture-*.png -> screenshot-*.png,
    # except the glance one — that's synthesized (see make_glance_screenshot).
    for src in sorted(HERE.glob("capture-*.png")):
        if "glance" in src.name:
            continue
        frame_capture(src, HERE / src.name.replace("capture-", "screenshot-", 1))
    make_glance_screenshot(HERE / "screenshot-8-glance.png")
