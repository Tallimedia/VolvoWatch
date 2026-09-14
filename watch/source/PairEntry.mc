import Toybox.Lang;
import Toybox.WatchUi;

//! In-app pairing: enter the numeric code from the connect page on the watch,
//! via a row of digit wheels. Works with no app-settings screen, so it covers
//! sideloads. On a store build, entering the code in Garmin Connect settings is
//! the easier path — this is the fallback.
module PairEntry {

    function supported() as Boolean {
        return true;   // Picker is available on every current device
    }

    function start(view as MainView) as Void {
        WatchUi.pushView(new CodePicker(), new CodePickerDelegate(view), WatchUi.SLIDE_LEFT);
    }
}
