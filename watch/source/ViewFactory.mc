import Toybox.Lang;
import Toybox.WatchUi;

//! Four scrollable pages: status, charging, trip, warnings. All read the
//! same cached /v1/status; MainView owns the fetch.
class ViewFactory extends WatchUi.ViewLoopFactory {
    private var _main as MainView;
    private var _charging as ChargingView;
    private var _trip as TripView;
    private var _warnings as WarningsView;

    function initialize() {
        ViewLoopFactory.initialize();
        _main = new MainView();
        _charging = new ChargingView(_main);
        _trip = new TripView(_main);
        _warnings = new WarningsView(_main);
    }

    function getView(page as Number) as
        [WatchUi.ViewLoopFactory.Views] or
        [WatchUi.ViewLoopFactory.Views, WatchUi.ViewLoopFactory.Delegates] {
        if (page == 1) {
            return [_charging, new PageDelegate(_main)];
        }
        if (page == 2) {
            return [_trip, new PageDelegate(_main)];
        }
        if (page == 3) {
            return [_warnings, new PageDelegate(_main)];
        }
        return [_main, new MainDelegate(_main)];
    }

    function getSize() as Number {
        return 4;
    }
}
