import Toybox.Graphics;
import Toybox.Lang;
import Toybox.WatchUi;

//! Page 4: every active warning as an icon + one line, or "No active
//! warnings" when there's nothing to report. Unlike the other pages this is
//! a variable-length list, not a fixed hero + rows layout.
class WarningsView extends WatchUi.View {

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

        _drawVersionFooter(dc, cx, h);

        var s = Store.cachedStatus();
        if (s == null) {
            dc.setColor(Theme.MUTED, Graphics.COLOR_TRANSPARENT);
            dc.drawText(cx, h / 2 - 12, Graphics.FONT_SMALL, "No data yet", hc);
            return;
        }

        // Dev builds can force every advisory on to eyeball the layout.
        var fake = DevConfig.FAKE_FLAGS;

        var icons = [] as Array<WatchUi.BitmapResource>;
        var texts = [] as Array<String>;

        if (s["doors_closed"] == false || fake) {
            icons.add(WatchUi.loadResource(Rez.Drawables.IconFault));
            texts.add("Check doors");
        }
        if (s["windows_closed"] == false || fake) {
            icons.add(WatchUi.loadResource(Rez.Drawables.IconFault));
            texts.add("Check windows");
        }
        if (s["service_due"] == true || fake) {
            icons.add(WatchUi.loadResource(Rez.Drawables.IconService));
            var km = Fmt.num(s["service_in_km"]);
            texts.add(km != null ? "Service due · " + Fmt.km(km) : "Service due");
        }
        if (s["washer_fluid_low"] == true || fake) {
            icons.add(WatchUi.loadResource(Rez.Drawables.IconWasher));
            texts.add("Washer fluid low");
        }
        if (s["tyre_warning"] == true || fake) {
            icons.add(WatchUi.loadResource(Rez.Drawables.IconTyre));
            texts.add("Tyre pressure warning");
        }

        if (icons.size() == 0) {
            dc.setColor(Theme.OK, Graphics.COLOR_TRANSPARENT);
            dc.drawText(cx, h / 2 - 12, Graphics.FONT_SMALL, "No active warnings", hc);
            return;
        }

        var valF = Graphics.FONT_SMALL;
        var ROWH = 56;
        var gap = 14; // icon-to-text gap

        var totalH = icons.size() * ROWH;
        var y = (h - totalH) / 2;
        if (y < h * 0.08) { y = h * 0.08; }

        // Round screens narrow toward top/bottom; a row wider than this on a
        // small device (e.g. "Service due · 15000 km") would run past the
        // bezel, so it drops to a smaller font rather than clipping.
        var maxRowW = dc.getWidth() * 0.86;

        for (var i = 0; i < icons.size(); i++) {
            var bmp = icons[i];
            var text = texts[i];
            var font = valF;
            var textW = dc.getTextWidthInPixels(text, font);
            if (bmp.getWidth() + gap + textW > maxRowW) {
                font = Graphics.FONT_XTINY;
                textW = dc.getTextWidthInPixels(text, font);
            }
            var rowW = bmp.getWidth() + gap + textW;
            var rowCy = y + ROWH / 2;

            var iconX = cx - rowW / 2;
            dc.drawBitmap(iconX.toNumber(), (rowCy - bmp.getHeight() / 2).toNumber(), bmp);

            dc.setColor(Theme.TEXT, Graphics.COLOR_TRANSPARENT);
            dc.drawText(
                (iconX + bmp.getWidth() + gap).toNumber(),
                rowCy.toNumber(),
                font, text, Graphics.TEXT_JUSTIFY_LEFT | Graphics.TEXT_JUSTIFY_VCENTER);

            y += ROWH;
        }
    }

    //! Same style/position as the status page's footer — lets a tester
    //! confirm which build is actually installed.
    private function _drawVersionFooter(dc as Dc, cx as Number, h as Number) as Void {
        var vc = Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER;
        dc.setColor(Theme.DIM, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.885, Graphics.FONT_XTINY,
            "v" + (WatchUi.loadResource(Rez.Strings.AppVersion) as String), vc);
    }
}
