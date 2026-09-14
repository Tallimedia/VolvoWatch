import Toybox.Graphics;
import Toybox.Lang;
import Toybox.WatchUi;

//! Page 3: the big odometer — handy when a fuel card asks for the mileage —
//! average fuel use, and the trip meters. Rows with no data are left out.
class TripView extends WatchUi.View {

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

        var rows = [] as Array<Array<String>>;
        var avg = Fmt.num(s["avg_fuel_l_100"]);
        if (avg != null) {
            rows.add(["AVG FUEL", avg.format("%.1f") + " l/100"]);
        }
        var trip = Fmt.num(s["trip_km"]);
        if (trip != null) {
            rows.add(["TRIP", trip.format("%.1f") + " km"]);
        }
        var tripAuto = Fmt.num(s["trip_auto_km"]);
        if (tripAuto != null) {
            rows.add(["TRIP (AUTO)", tripAuto.format("%.1f") + " km"]);
        }

        // Lay out top-justified, advancing by the real font heights so nothing
        // can collide regardless of the device's font metrics.
        var labelF = Graphics.FONT_XTINY;
        var heroF = Graphics.FONT_NUMBER_MEDIUM;
        var valF = Graphics.FONT_SMALL;
        var lh = dc.getFontHeight(labelF);
        var hh = dc.getFontHeight(heroF);
        var vh = dc.getFontHeight(valF);
        var ROWGAP = 16;

        var totalH = lh + 2 + hh + rows.size() * (ROWGAP + lh + 2 + vh);
        var y = (h - totalH) / 2;
        if (y < h * 0.06) { y = h * 0.06; }

        dc.setColor(Theme.MUTED, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, y, labelF, "ODOMETER  ·  KM", hc);
        y += lh + 2;
        dc.setColor(Theme.TEXT, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, y, heroF, Fmt.grouped(s["odometer_km"]), hc);
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
