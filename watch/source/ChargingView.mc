import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Math;
import Toybox.WatchUi;

//! Page 2: battery %, a charging-bolt badge when plugged in and drawing
//! power, and (while plugged in) time to full / charging power. Rows with no
//! data are simply left out.
class ChargingView extends WatchUi.View {

    //! `main` is kept only so the factory can build view + delegate together.
    function initialize(main as MainView) {
        View.initialize();
    }

    function onShow() as Void {
        // MainView drives the fetch; nudge it if the cache is stale.
        if (PageStatus.shouldRefresh()) {
            Backend.status(method(:onStatus));
        }
    }

    function onStatus(ok as Boolean, payload as Dictionary or String or Null) as Void {
        PageStatus.applyStatus(ok, payload);
    }

    function onUpdate(dc as Dc) as Void {
        dc.setColor(Theme.TEXT, Graphics.COLOR_BLACK);
        dc.clear();
        var cx = dc.getWidth() / 2;
        var h = dc.getHeight();
        var hc = Graphics.TEXT_JUSTIFY_CENTER;

        var s = Store.cachedStatus();
        if (s == null) {
            dc.setColor(Theme.MUTED, Graphics.COLOR_TRANSPARENT);
            dc.drawText(cx, h / 2 - 12, Graphics.FONT_SMALL, "No data yet", hc);
            return;
        }

        // Same "is it charging" signal the main screen's bolt icon uses, not
        // just plugged_in — belt and suspenders in case that derived field
        // ever lags the raw charging status (it did once: backend bug fixed
        // 2026-09-05, `plugged_in` required an exact "CONNECTED" match that a
        // charging-specific connector-status variant could fail). Exact match
        // on "charging" — "done"/"scheduled"/"fault" are also non-"idle" but
        // are not actively drawing power.
        var charging = s["charging"];
        var isCharging = (charging instanceof String) && (charging as String).equals("charging");
        var plugged = s["plugged_in"] == true || isCharging;

        var rows = [] as Array<Array<String>>;
        if (plugged) {
            var ttf = Fmt.num(s["time_to_full_min"]);
            if (ttf != null && ttf > 0) {
                rows.add(["TIME TO FULL", Fmt.duration(ttf.toNumber())]);
            }
            // Not shown on the XC60 — Volvo returns PROPERTY_NOT_FOUND for
            // chargingPower even mid-charge (confirmed 2026-09-13, not a bug).
            // Left in for vehicles/sessions where Volvo does report it.
            var pw = Fmt.num(s["charging_power_w"]);
            if (pw != null && pw > 0) {
                rows.add(["CHARGING POWER", (pw / 1000.0).format("%.1f") + " kW"]);
            }
        }

        // Lay out top-justified, advancing by the real font heights so nothing
        // can collide regardless of the device's font metrics.
        var labelF = Graphics.FONT_XTINY;
        // FONT_NUMBER_MEDIUM has no "%" glyph (numerals only, same reason the
        // odometer stays unit-free) — this hero needs the % inline, so it
        // uses a regular font instead, at some size cost.
        var heroF = Graphics.FONT_LARGE;
        var valF = Graphics.FONT_SMALL;
        var lh = dc.getFontHeight(labelF);
        var hh = dc.getFontHeight(heroF);
        var vh = dc.getFontHeight(valF);
        var ROWGAP = 16;

        var totalH = lh + 2 + hh + rows.size() * (ROWGAP + lh + 2 + vh);
        var y = (h - totalH) / 2;
        if (y < h * 0.06) { y = h * 0.06; }

        // Label + bolt (+ AC/DC when known) are centered as one group — the
        // bolt is always shown here (unlike the status row's bolt, which
        // only appears while charging), coloured green/red for charging/not
        // so it reads as a state indicator rather than a presence/absence
        // flag.
        var chargingType = s["charging_type"];
        var typeStr = null;
        if (chargingType instanceof String) {
            var ct = (chargingType as String).toUpper();
            if (ct.equals("AC") || ct.equals("DC")) {
                typeStr = ct;
            }
        }

        var label = "BATTERY";
        var labelW = dc.getTextWidthInPixels(label, labelF);
        var boltGap = 8;
        var bolt = WatchUi.loadResource(
            isCharging ? Rez.Drawables.IconBoltGreen : Rez.Drawables.IconBoltRed);
        var typeGap = (typeStr != null) ? 6 : 0;
        var typeW = (typeStr != null) ? dc.getTextWidthInPixels(typeStr as String, labelF) : 0;
        var labelGroupW = labelW + boltGap + bolt.getWidth() + typeGap + typeW;
        var labelStartX = cx - labelGroupW / 2;

        dc.setColor(Theme.MUTED, Graphics.COLOR_TRANSPARENT);
        dc.drawText(labelStartX.toNumber(), y, labelF, label, Graphics.TEXT_JUSTIFY_LEFT);
        var boltX = labelStartX + labelW + boltGap;
        dc.drawBitmap(
            boltX.toNumber(),
            (y + lh / 2 - bolt.getHeight() / 2).toNumber(),
            bolt);
        if (typeStr != null) {
            dc.drawText(
                (boltX + bolt.getWidth() + typeGap).toNumber(), y, labelF,
                typeStr as String, Graphics.TEXT_JUSTIFY_LEFT);
        }
        y += lh + 2;

        // Hero: battery %, with the unit inline this time.
        var battPct = Fmt.num(s["battery_pct"]);
        var heroStr = (battPct != null) ? Math.round(battPct).format("%d") + "%" : Fmt.DASH;
        dc.setColor(Theme.batteryColour(battPct), Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, y, heroF, heroStr, hc);
        y += hh;

        for (var i = 0; i < rows.size(); i++) {
            y += ROWGAP;
            dc.setColor(Theme.MUTED, Graphics.COLOR_TRANSPARENT);
            dc.drawText(cx, y, labelF, rows[i][0], hc);
            y += lh + 2;
            dc.setColor(Theme.TEXT, Graphics.COLOR_TRANSPARENT);
            dc.drawText(cx, y, valF, rows[i][1], hc);
            y += vh;
        }
    }
}
