import Toybox.Lang;
import Toybox.WatchUi;

//! Input shared by every secondary page (charging / trip / warnings). A press
//! opens the same action menu as the main screen (command results land on
//! MainView, visible when you swipe back to it).
class PageDelegate extends WatchUi.BehaviorDelegate {
    private var _main as MainView;

    function initialize(main as MainView) {
        BehaviorDelegate.initialize();
        _main = main;
    }

    function onSelect() as Boolean {
        if (!_main.isPaired()) {
            PairEntry.start(_main);
            return true;
        }
        new MainDelegate(_main).openMenu();
        return true;
    }

    function onMenu() as Boolean {
        return onSelect();
    }
}
