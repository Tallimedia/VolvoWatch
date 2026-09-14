import Toybox.Application;
import Toybox.Graphics;
import Toybox.Lang;
import Toybox.WatchUi;

//! VolvoWatch — glance + widget showing Volvo status and starting climatisation,
//! talking to the self-hosted backend (see ../backend).
class VolvoWatchApp extends Application.AppBase {

    function initialize() {
        AppBase.initialize();
    }

    function onStart(state as Dictionary?) as Void {
    }

    function onStop(state as Dictionary?) as Void {
    }

    //! Status page, then charging / trip / warnings pages you scroll down to.
    function getInitialView() as [WatchUi.Views] or [WatchUi.Views, WatchUi.InputDelegates] {
        if (WatchUi has :ViewLoop) {
            var loop = new WatchUi.ViewLoop(
                new ViewFactory(), { :page => 0, :wrap => false });
            return [loop, new WatchUi.ViewLoopDelegate(loop)];
        }
        var view = new MainView();
        return [view, new MainDelegate(view)];
    }

    //! Small card in the glance loop.
    function getGlanceView() as [WatchUi.GlanceView] or [WatchUi.GlanceView, WatchUi.GlanceViewDelegate] or Null {
        return [new GlanceView()];
    }

    //! Settings changed in Garmin Connect — drop the paired token if the URL
    //! changed, and refresh.
    function onSettingsChanged() as Void {
        Store.onSettingsChanged();
        WatchUi.requestUpdate();
    }
}
