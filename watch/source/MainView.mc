import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Timer;
import Toybox.WatchUi;

//! Full widget view: vehicle status + entry point to the action menu.
class MainView extends WatchUi.View {

    enum State { LOADING, READY, NEEDS_SETUP, PAIRING, ERROR }

    //! How long a command result ("Done", "Car: TIMEOUT") stays in the footer
    //! before it is replaced by the usual freshness line.
    private const RESULT_LINGER_MS = 4000;

    private var _state as State = LOADING;
    private var _errorKey as String = "";
    private var _busyMsg as String? = null;   // transient command result
    private var _resultTimer as Timer.Timer? = null;

    function initialize() {
        View.initialize();
    }

    function onLayout(dc as Dc) as Void {
    }

    function onShow() as Void {
        refresh();
    }

    function onHide() as Void {
        _stopResultTimer();
    }

    private function _stopResultTimer() as Void {
        if (_resultTimer != null) {
            (_resultTimer as Timer.Timer).stop();
            _resultTimer = null;
        }
    }

    //! Drop the transient command message and pull fresh status.
    function onResultExpired() as Void {
        _stopResultTimer();
        _busyMsg = null;
        WatchUi.requestUpdate();
        Backend.status(method(:onStatus));
    }

    //! Kick off pairing (if needed) then a status fetch.
    function refresh() as Void {
        _stopResultTimer();
        _busyMsg = null;
        if (Store.deviceToken() == null) {
            var code = Store.pairingCode();
            if (code == null) {
                _state = NEEDS_SETUP;
                WatchUi.requestUpdate();
                return;
            }
            _state = PAIRING;
            WatchUi.requestUpdate();
            Backend.pair(code, method(:onPair));
            return;
        }
        if (Store.cachedStatus() == null) {
            _state = LOADING;
        }
        WatchUi.requestUpdate();
        Backend.status(method(:onStatus));
    }

    //! Called by PairEntry after the user types a code on the watch.
    function pairWithCode(code as String) as Void {
        _state = PAIRING;
        _busyMsg = null;
        WatchUi.requestUpdate();
        Backend.pair(code, method(:onPair));
    }

    function onPair(ok as Boolean, payload as Dictionary or String or Null) as Void {
        if (ok && payload instanceof Dictionary) {
            var token = (payload as Dictionary)["device_token"];
            if (token instanceof String) {
                Store.setDeviceToken(token as String);
                Store.clearPairingCode();
                _state = LOADING;
                WatchUi.requestUpdate();
                Backend.status(method(:onStatus));
                return;
            }
        }
        _state = ERROR;
        _errorKey = "pair";
        WatchUi.requestUpdate();
    }

    function isPaired() as Boolean {
        return Store.deviceToken() != null;
    }

    function onStatus(ok as Boolean, payload as Dictionary or String or Null) as Void {
        if (ok && payload instanceof Dictionary) {
            var d = payload as Dictionary;
            if (d["needs_reconnect"] == true) {
                _state = ERROR;
                _errorKey = "reconnect";
            } else {
                Store.setStatus(d);
                _state = READY;
                _errorKey = "";
            }
        } else if (payload instanceof String && (payload as String).equals("auth")) {
            Store.clearDeviceToken();
            _state = NEEDS_SETUP;
        } else {
            // keep showing cached data if we have it
            _state = (Store.cachedStatus() != null) ? READY : ERROR;
            _errorKey = (payload instanceof String) ? payload as String : "net";
        }
        WatchUi.requestUpdate();
    }

    //! Called by the delegate the moment a command is sent.
    function markCommandSent(cmd as String) as Void {
        _busyMsg = cmd.equals("climate-start") ? "Starting climate…" : "Stopping climate…";
        WatchUi.requestUpdate();
    }

    //! Called by the delegate after a command round-trips.
    //! payload: the backend's CommandResult dict, or an error key string.
    function showCommandResult(ok as Boolean, payload as Dictionary or String or Null) as Void {
        if (ok && payload instanceof Dictionary) {
            var d = payload as Dictionary;
            if (d["ok"] == true) {
                _busyMsg = "Done";
            } else {
                var st = d["invoke_status"];
                _busyMsg = (st instanceof String) ? "Car: " + (st as String) : "Not confirmed";
            }
        } else if (payload instanceof String) {
            _busyMsg = errorTextFor(payload as String);
        } else {
            _busyMsg = "Command failed";
        }
        WatchUi.requestUpdate();

        // Leave the result on screen long enough to read, then refresh.
        _stopResultTimer();
        _resultTimer = new Timer.Timer();
        (_resultTimer as Timer.Timer).start(method(:onResultExpired), RESULT_LINGER_MS, false);
    }

    function onUpdate(dc as Dc) as Void {
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_BLACK);
        dc.clear();
        var cx = dc.getWidth() / 2;
        var h = dc.getHeight();

        dc.setColor(Theme.MUTED, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.155, Graphics.FONT_XTINY, Store.carLabel(),
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);

        if (_state == NEEDS_SETUP) {
            _center(dc, cx, h, Graphics.FONT_SMALL, "Press to enter\nthe pairing code");
            return;
        }
        if (_state == PAIRING) {
            _center(dc, cx, h, Graphics.FONT_SMALL, "Pairing…");
            return;
        }

        var status = Store.cachedStatus();
        if (status == null) {
            _center(dc, cx, h, Graphics.FONT_SMALL,
                _state == ERROR ? errorText() : "Loading…");
            return;
        }

        drawStatus(dc, cx, h, status);
    }

    function drawStatus(dc as Dc, cx as Number, h as Number, s as Dictionary) as Void {
        var vc = Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER;

        // Hero: combined range — colour by how far it can still go.
        var rangeKm = Fmt.num(s["range_km"]);
        dc.setColor(Theme.rangeColour(rangeKm), Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.34, Graphics.FONT_NUMBER_MEDIUM, Fmt.intStr(s["range_km"]), vc);
        // PHEV: when both a fuel and an electric range come back, the hero is
        // their sum — say so.
        var fr = Fmt.num(s["fuel_range_km"]);
        var br = Fmt.num(s["battery_range_km"]);
        var rangeLabel = (fr != null && fr > 0 && br != null && br > 0)
            ? "km tot range" : "km range";
        dc.setColor(Theme.MUTED, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.48, Graphics.FONT_XTINY, rangeLabel, vc);

        // Battery / fuel — battery figure reddens when low. A pure EV has no
        // fuel_pct at all (Volvo reports fuelAmount: null, not 0) — show just
        // the battery figure, centred alone, rather than a stray "Fuel –".
        var battFont = Graphics.FONT_SMALL;
        var battTxt = "Bat " + Fmt.pct(s["battery_pct"]);
        var y = h * 0.585;
        dc.setColor(Theme.batteryColour(Fmt.num(s["battery_pct"])), Graphics.COLOR_TRANSPARENT);
        if (s["fuel_pct"] == null) {
            dc.drawText(cx, y, battFont, battTxt, vc);
        } else {
            var fuelTxt = "Fuel " + Fmt.pct(s["fuel_pct"]);
            var gap = "    ";
            var battW = dc.getTextWidthInPixels(battTxt, battFont);
            var fullW = dc.getTextWidthInPixels(battTxt + gap + fuelTxt, battFont);
            var leftX = cx - fullW / 2;
            dc.drawText(leftX, y, battFont, battTxt,
                Graphics.TEXT_JUSTIFY_LEFT | Graphics.TEXT_JUSTIFY_VCENTER);
            dc.setColor(Theme.TEXT, Graphics.COLOR_TRANSPARENT);
            dc.drawText(leftX + battW + dc.getTextWidthInPixels(gap, battFont), y, battFont, fuelTxt,
                Graphics.TEXT_JUSTIFY_LEFT | Graphics.TEXT_JUSTIFY_VCENTER);
        }

        drawFlagIcons(dc, cx, (h * 0.695).toNumber(), s);

        // Odometer (handy at the pump) + freshness / transient message, stacked.
        var odo = Fmt.odometer(s["odometer_km"]);
        if (!odo.equals(Fmt.DASH)) {
            dc.setColor(Theme.MUTED, Graphics.COLOR_TRANSPARENT);
            dc.drawText(cx, h * 0.80, Graphics.FONT_XTINY, odo, vc);
        }

        var footer;
        if (_busyMsg != null) {
            footer = _busyMsg;
        } else if (_state == ERROR) {
            footer = errorText();
        } else if (s["car_reachable"] == false) {
            footer = "Car asleep · " + Fmt.ago(Store.statusAgeSeconds());
        } else {
            footer = "Updated " + Fmt.ago(Store.statusAgeSeconds());
        }
        dc.setColor(Theme.DIM, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.885, Graphics.FONT_XTINY, footer, vc);
    }

    //! Row of status glyphs: lock, warning (service / something open), charging.
    function drawFlagIcons(dc as Dc, cx as Number, cy as Number, s as Dictionary) as Void {
        var step = 52;

        var locked = s["locked"];
        var charging = s["charging"];
        // Exact match on "charging" — "done"/"scheduled"/"fault" are also
        // non-"idle" but are not actively drawing power, so a blanket
        // not-idle check would show the bolt as healthy for a finished or
        // faulted session.
        var showBolt = charging instanceof String && (charging as String).equals("charging");

        // Dev builds can force every advisory on to eyeball the row.
        var fake = DevConfig.FAKE_FLAGS;

        var icons = [] as Array<WatchUi.BitmapResource>;
        if (locked instanceof Boolean) {
            icons.add(WatchUi.loadResource(
                (locked as Boolean) ? Rez.Drawables.IconLockClosed : Rez.Drawables.IconLockOpen));
        }
        // A door/window left open is a "look now" alert (red triangle).
        if (s["all_closed"] == false) {
            icons.add(WatchUi.loadResource(Rez.Drawables.IconFault));
        }
        // A service reminder is maintenance, not a fault — a wrench, never red.
        if (s["service_due"] == true || fake) {
            icons.add(WatchUi.loadResource(Rez.Drawables.IconService));
        }
        // Washer fluid / tyre pressure — amber advisories, shown only when set.
        if (s["washer_fluid_low"] == true || fake) {
            icons.add(WatchUi.loadResource(Rez.Drawables.IconWasher));
        }
        if (s["tyre_warning"] == true || fake) {
            icons.add(WatchUi.loadResource(Rez.Drawables.IconTyre));
        }
        if (showBolt) {
            icons.add(WatchUi.loadResource(Rez.Drawables.IconBoltGreen));
        } else if (s["car_reachable"] == false && s["unreachable_reason"] instanceof String
                && (s["unreachable_reason"] as String).equals("CAR_IN_USE")) {
            // Not charging, but Volvo's command-accessibility check says the
            // car is actively being driven right now — a steering wheel,
            // same neutral blue as the bolt (an activity state, not a
            // warning). Mutually exclusive with the bolt on purpose.
            icons.add(WatchUi.loadResource(Rez.Drawables.IconInUse));
        }
        if (icons.size() == 0) { return; }

        var x = cx - (icons.size() - 1) * step / 2;
        for (var i = 0; i < icons.size(); i++) {
            var bmp = icons[i];
            dc.drawBitmap(x - bmp.getWidth() / 2, cy - bmp.getHeight() / 2, bmp);
            x += step;
        }
    }

    function errorText() as String {
        return errorTextFor(_errorKey);
    }

    function errorTextFor(key as String) as String {
        if (key.equals("phone")) { return "Phone not connected"; }
        if (key.equals("reconnect")) { return "Reconnect Volvo\n(open the connect page)"; }
        if (key.equals("rate")) { return "Busy — try again"; }
        if (key.equals("pair")) { return "Pairing failed —\ncheck the code"; }
        return "Can't reach backend";
    }

    function _center(dc as Dc, cx as Number, h as Number, font as Graphics.FontType, text as String) as Void {
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h / 2, font, text,
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
    }

    function ready() as Boolean {
        return _state == READY;
    }
}
