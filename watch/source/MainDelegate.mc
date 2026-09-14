import Toybox.Communications;
import Toybox.Lang;
import Toybox.WatchUi;

//! Widget input: any select/menu press opens the action menu.
class MainDelegate extends WatchUi.BehaviorDelegate {
    private var _view as MainView;

    function initialize(view as MainView) {
        BehaviorDelegate.initialize();
        _view = view;
    }

    function onSelect() as Boolean {
        // Not paired yet: a press goes straight to the code keyboard.
        if (!_view.isPaired() && PairEntry.supported()) {
            PairEntry.start(_view);
            return true;
        }
        openMenu();
        return true;
    }

    function onMenu() as Boolean {
        return onSelect();
    }

    function openMenu() as Void {
        var menu = new WatchUi.Menu2({ :title => "Volvo" });
        menu.addItem(new WatchUi.MenuItem(
            WatchUi.loadResource(Rez.Strings.StartClimate) as String, null, :climateStart, null));
        // "Stop climate" hidden as of 1.2.0 — Volvo's public API reports the
        // command as COMPLETED but doesn't reliably stop the car (confirmed
        // on 3 cars across 2 platforms; an independent implementation, Home
        // Assistant's Volvo integration, hits the identical wall). Not
        // fixable client-side. Re-add the addItem call below once Volvo
        // fixes it upstream — ActionMenuDelegate still handles :climateStop.
        // menu.addItem(new WatchUi.MenuItem(
        //     WatchUi.loadResource(Rez.Strings.StopClimate) as String, null, :climateStop, null));
        menu.addItem(new WatchUi.MenuItem(
            WatchUi.loadResource(Rez.Strings.Refresh) as String, null, :refresh, null));
        if (PairEntry.supported()) {
            menu.addItem(new WatchUi.MenuItem(
                WatchUi.loadResource(Rez.Strings.EnterCode) as String, null, :pair, null));
        }
        menu.addItem(new WatchUi.MenuItem(
            WatchUi.loadResource(Rez.Strings.OpenConnectPage) as String, null, :openConnectPage, null));
        WatchUi.pushView(menu, new ActionMenuDelegate(_view), WatchUi.SLIDE_UP);
    }
}

//! Handles picks from the action menu.
class ActionMenuDelegate extends WatchUi.Menu2InputDelegate {
    private var _view as MainView;

    function initialize(view as MainView) {
        Menu2InputDelegate.initialize();
        _view = view;
    }

    function onSelect(item as WatchUi.MenuItem) as Void {
        var id = item.getId();
        if (id == :refresh) {
            WatchUi.popView(WatchUi.SLIDE_DOWN);
            _view.refresh();
            return;
        }
        if (id == :pair) {
            WatchUi.popView(WatchUi.SLIDE_DOWN);
            PairEntry.start(_view);
            return;
        }
        if (id == :openConnectPage) {
            WatchUi.popView(WatchUi.SLIDE_DOWN);
            // Pushes a phone notification (GCM) the user taps to open the
            // browser there — the watch itself has no browser. Only works
            // over Bluetooth to a connected phone, not WiFi-only.
            Communications.openWebPage(Store.backendUrl() + "/link", null, null);
            return;
        }

        var prompt = (id == :climateStart)
            ? WatchUi.loadResource(Rez.Strings.ConfirmStartClimate) as String
            : WatchUi.loadResource(Rez.Strings.ConfirmStopClimate) as String;
        var cmd = (id == :climateStart) ? "climate-start" : "climate-stop";

        // Replace the menu with the confirmation, so answering it returns
        // straight to MainView (the Confirmation view dismisses itself).
        WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
        WatchUi.pushView(
            new WatchUi.Confirmation(prompt),
            new CommandConfirmDelegate(_view, cmd),
            WatchUi.SLIDE_UP
        );
    }

    function onBack() as Void {
        WatchUi.popView(WatchUi.SLIDE_DOWN);
    }
}

//! Fires the command on Yes. The Confirmation view dismisses itself on response,
//! returning to MainView (the menu was already popped).
class CommandConfirmDelegate extends WatchUi.ConfirmationDelegate {
    private var _view as MainView;
    private var _cmd as String;

    function initialize(view as MainView, cmd as String) {
        ConfirmationDelegate.initialize();
        _view = view;
        _cmd = cmd;
    }

    function onResponse(response as WatchUi.Confirm) as Boolean {
        if (response == WatchUi.CONFIRM_YES) {
            _view.markCommandSent(_cmd);
            Backend.command(_cmd, method(:onCommand));
        }
        return true;
    }

    function onCommand(ok as Boolean, payload as Dictionary or String or Null) as Void {
        _view.showCommandResult(ok, payload);
    }
}
