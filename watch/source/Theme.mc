import Toybox.Graphics;
import Toybox.Lang;

//! Colour decisions in one place. Softer than the stock COLOR_* on AMOLED.
(:glance)
module Theme {

    const TEXT = 0xF5F8FD;      // near-white
    const MUTED = 0x96A6C2;     // grey
    const DIM = 0x62708A;       // dimmer grey, for the footer
    const OK = 0x8FD18F;        // muted green
    const WARN = 0xF2B24A;      // amber
    const BAD = 0xF06060;       // soft red (not COLOR_RED)
    const ACCENT = 0x5E94FF;    // blue

    // Range (km) below which the hero number turns amber, then red.
    const RANGE_WARN_KM = 150;
    const RANGE_BAD_KM = 100;

    // Battery % below which the figure turns amber, then red.
    const BATTERY_WARN = 15;
    const BATTERY_BAD = 8;

    function rangeColour(km as Float?) as Number {
        if (km == null) { return TEXT; }
        if (km < RANGE_BAD_KM) { return BAD; }
        if (km < RANGE_WARN_KM) { return WARN; }
        return TEXT;
    }

    function batteryColour(pct as Float?) as Number {
        if (pct == null) { return TEXT; }
        if (pct < BATTERY_BAD) { return BAD; }
        if (pct < BATTERY_WARN) { return WARN; }
        return TEXT;
    }
}
