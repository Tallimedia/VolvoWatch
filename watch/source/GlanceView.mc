import Toybox.Graphics;
import Toybox.Lang;
import Toybox.WatchUi;

//! Small card in the glance loop: battery %, fuel %, combined range.
//! Renders the cached status immediately; refreshes it if stale.
(:glance)
class GlanceView extends WatchUi.GlanceView {

    function initialize() {
        GlanceView.initialize();
    }

    function onShow() as Void {
        if (PageStatus.shouldRefresh()) {
            Backend.status(method(:onStatus));
        }
    }

    function onStatus(ok as Boolean, payload as Dictionary or String or Null) as Void {
        PageStatus.applyStatus(ok, payload);
    }

    function onUpdate(dc as Dc) as Void {
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        dc.clear();

        var h = dc.getHeight();
        var status = Store.cachedStatus();
        var name = Store.carLabel();

        if (Store.deviceToken() == null && Store.pairingCode() == null) {
            dc.drawText(0, h / 2, Graphics.FONT_GLANCE, name + " — set up in settings",
                Graphics.TEXT_JUSTIFY_LEFT | Graphics.TEXT_JUSTIFY_VCENTER);
            return;
        }

        if (status == null) {
            dc.drawText(0, h / 2, Graphics.FONT_GLANCE, name + " — loading…",
                Graphics.TEXT_JUSTIFY_LEFT | Graphics.TEXT_JUSTIFY_VCENTER);
            return;
        }

        var battery = Fmt.pct(status["battery_pct"]);
        var fuel = Fmt.pct(status["fuel_pct"]);
        var range = Fmt.km(status["range_km"]);

        dc.drawText(0, h * 0.28, Graphics.FONT_GLANCE, name,
            Graphics.TEXT_JUSTIFY_LEFT | Graphics.TEXT_JUSTIFY_VCENTER);

        var statsY = h * 0.72;
        var vc = Graphics.TEXT_JUSTIFY_LEFT | Graphics.TEXT_JUSTIFY_VCENTER;
        var font = Graphics.FONT_GLANCE_NUMBER;

        var rest = [];
        if (!fuel.equals("–")) { rest.add("Fuel " + fuel); }
        if (!range.equals("–")) { rest.add(range); }
        var restText = Fmt.join(rest, "   ");

        if (battery.equals("–")) {
            dc.setColor(Theme.TEXT, Graphics.COLOR_TRANSPARENT);
            dc.drawText(0, statsY, font, restText.length() > 0 ? restText : "no data", vc);
            return;
        }

        // "Bat X%" turns green while actively charging instead of a separate
        // bolt icon — simpler than fitting/positioning a bitmap on a canvas
        // this small (and avoids the glance-scope resource dance).
        var charging = status["charging"];
        var isCharging = charging instanceof String && (charging as String).equals("charging");
        var batColor = isCharging ? Theme.OK : Theme.batteryColour(Fmt.num(status["battery_pct"]));
        var batText = "Bat " + battery + (rest.size() > 0 ? "   " : "");

        dc.setColor(batColor, Graphics.COLOR_TRANSPARENT);
        dc.drawText(0, statsY, font, batText, vc);

        if (rest.size() > 0) {
            var batW = dc.getTextWidthInPixels(batText, font);
            dc.setColor(Theme.TEXT, Graphics.COLOR_TRANSPARENT);
            dc.drawText(batW, statsY, font, restText, vc);
        }
    }
}
