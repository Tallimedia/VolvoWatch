import Toybox.Graphics;
import Toybox.Lang;
import Toybox.WatchUi;

//! A row of digit wheels for entering the numeric pairing code.
//! Far kinder on a round watch than the on-screen keyboard.

const CODE_LEN = 6;

class CodePicker extends WatchUi.Picker {
    function initialize() {
        var title = new WatchUi.Text({
            :text => WatchUi.loadResource(Rez.Strings.EnterCode) as String,
            :locX => WatchUi.LAYOUT_HALIGN_CENTER,
            :locY => WatchUi.LAYOUT_VALIGN_BOTTOM,
            :color => Graphics.COLOR_LT_GRAY,
        });
        var pattern = new [$.CODE_LEN] as Array<WatchUi.PickerFactory>;
        for (var i = 0; i < $.CODE_LEN; i++) {
            pattern[i] = new DigitFactory();
        }
        Picker.initialize({ :title => title, :pattern => pattern });
    }

    function onUpdate(dc as Dc) as Void {
        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();
        Picker.onUpdate(dc);
    }
}

class DigitFactory extends WatchUi.PickerFactory {
    function initialize() {
        PickerFactory.initialize();
    }

    function getSize() as Number {
        return 10;
    }

    function getValue(index as Number) as Object? {
        return index;   // 0..9
    }

    function getDrawable(index as Number, selected as Boolean) as Drawable? {
        return new WatchUi.Text({
            :text => index.toString(),
            :color => selected ? Graphics.COLOR_WHITE : Graphics.COLOR_DK_GRAY,
            :font => Graphics.FONT_NUMBER_MILD,
            :locX => WatchUi.LAYOUT_HALIGN_CENTER,
            :locY => WatchUi.LAYOUT_VALIGN_CENTER,
        });
    }
}

class CodePickerDelegate extends WatchUi.PickerDelegate {
    private var _view as MainView;

    function initialize(view as MainView) {
        PickerDelegate.initialize();
        _view = view;
    }

    function onCancel() as Boolean {
        WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
        return true;
    }

    function onAccept(values as Array) as Boolean {
        var code = "";
        for (var i = 0; i < values.size(); i++) {
            var v = values[i];
            code += (v instanceof Number) ? (v as Number).toString() : "0";
        }
        WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
        _view.pairWithCode(code);
        return true;
    }
}
