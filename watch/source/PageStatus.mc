import Toybox.Lang;
import Toybox.WatchUi;

//! Shared onShow/onStatus logic for every secondary page (Glance, Charging,
//! Trip, Warnings) — MainView drives the actual fetch cadence; these just
//! nudge it when their own cached view is stale, and apply whatever comes
//! back. Pulled out so the needs_reconnect guard only needs fixing in one
//! place instead of four identical copies.
(:glance)
module PageStatus {
    //! True if this page should kick off its own refresh (device paired,
    //! and the cache is missing or older than 5 minutes).
    function shouldRefresh() as Boolean {
        var age = Store.statusAgeSeconds();
        return Store.deviceToken() != null && (age == null || age > 300);
    }

    //! Store a successful status response — unless it's a needs_reconnect
    //! payload, which carries none of the vehicle fields and would clobber
    //! the last known-good cache.
    function applyStatus(ok as Boolean, payload as Dictionary or String or Null) as Void {
        if (ok && payload instanceof Dictionary) {
            var d = payload as Dictionary;
            if (d["needs_reconnect"] != true) {
                Store.setStatus(d);
            }
            WatchUi.requestUpdate();
        }
    }
}
