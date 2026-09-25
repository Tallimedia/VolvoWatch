import Toybox.Lang;
import Toybox.Math;

//! Small formatting helpers. All tolerate Null / Number / Float / String input
//! (values come straight from parsed JSON).
(:glance)
module Fmt {

    const DASH = "–";

    function num(v as Object?) as Float? {
        if (v instanceof Float) { return v as Float; }
        if (v instanceof Number) { return (v as Number).toFloat(); }
        if (v instanceof String) {
            var s = v as String;
            if (s.length() > 0) { return s.toFloat(); }
        }
        return null;
    }

    function pct(v as Object?) as String {
        var n = num(v);
        if (n == null) { return DASH; }
        return Math.round(n).format("%d") + "%";
    }

    //! km -> miles when Store.imperial() is set. UK/Ireland market only, so
    //! "imperial" here specifically means miles + UK gallons + UK mpg, not
    //! US units.
    function convKm(v as Object?) as Float? {
        var n = num(v);
        if (n == null) { return null; }
        return Store.imperial() ? n * 0.621371 : n;
    }

    //! "km" / "mi" for building custom labels around a converted distance.
    function distUnit() as String {
        return Store.imperial() ? "mi" : "km";
    }

    function km(v as Object?) as String {
        var n = convKm(v);
        if (n == null) { return DASH; }
        return Math.round(n).format("%d") + " " + distUnit();
    }

    //! Rounded integer as a bare string (no unit) — for hero numbers.
    function intStr(v as Object?) as String {
        var n = num(v);
        if (n == null) { return DASH; }
        return Math.round(n).format("%d");
    }

    //! Whole number with a thin-space thousands separator: 84231 -> "84 231".
    function grouped(v as Object?) as String {
        var n = num(v);
        if (n == null) { return DASH; }
        var digits = Math.round(n).format("%d");
        var out = "";
        var c = 0;
        for (var i = digits.length() - 1; i >= 0; i--) {
            if (c > 0 && c % 3 == 0) { out = " " + out; }
            out = digits.substring(i, i + 1) + out;
            c++;
        }
        return out;
    }

    //! Whole distance with a thin-space thousands separator: 84231 -> "84 231 km"
    //! (or the mile equivalent when imperial).
    function odometer(v as Object?) as String {
        var g = grouped(convKm(v));
        return g.equals(DASH) ? DASH : g + " " + distUnit();
    }

    //! Litres -> UK gallons when imperial.
    function litres(v as Object?) as String {
        var n = num(v);
        if (n == null) { return DASH; }
        return Store.imperial()
            ? (n / 4.54609).format("%.1f") + " gal"
            : n.format("%.1f") + " L";
    }

    //! Average consumption, L/100km -> UK mpg when imperial. Zero/negative is
    //! treated as no data — a real 0 L/100km isn't a value a car reports.
    function fuelConsumption(v as Object?) as String {
        var n = num(v);
        if (n == null || n <= 0) { return DASH; }
        return Store.imperial()
            ? (282.481 / n).format("%.1f") + " mpg"
            : n.format("%.1f") + " l/100km";
    }

    function boolText(v as Object?, yes as String, no as String) as String {
        if (v instanceof Boolean) {
            return (v as Boolean) ? yes : no;
        }
        return DASH;
    }

    function join(parts as Array<String>, sep as String) as String {
        var out = "";
        for (var i = 0; i < parts.size(); i++) {
            if (i > 0) { out += sep; }
            out += parts[i];
        }
        return out;
    }

    //! Minutes -> "45 min" / "2 h 10 min".
    function duration(minutes as Number?) as String {
        if (minutes == null || minutes <= 0) { return DASH; }
        if (minutes < 60) { return minutes.format("%d") + " min"; }
        var h = minutes / 60;
        var m = minutes % 60;
        return m == 0 ? h.format("%d") + " h" : h.format("%d") + " h " + m.format("%d") + " min";
    }

    //! Seconds -> "just now" / "3m ago" / "2h ago".
    function ago(seconds as Number?) as String {
        if (seconds == null) { return DASH; }
        if (seconds < 90) { return "just now"; }
        if (seconds < 3600) { return (seconds / 60).format("%d") + "m ago"; }
        return (seconds / 3600).format("%d") + "h ago";
    }
}
