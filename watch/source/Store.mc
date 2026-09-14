import Toybox.Application;
import Toybox.Application.Storage;
import Toybox.Lang;
import Toybox.System;
import Toybox.Time;

//! Persistent state: the paired device token and the last vehicle status.
//! Settings (backendUrl, pairingCode) live in Application.Properties.
(:glance)
module Store {

    const KEY_DEVICE_TOKEN = "deviceToken";
    const KEY_STATUS = "status";          // Dictionary from /v1/status
    const KEY_STATUS_TIME = "statusTime";  // epoch seconds when fetched
    const KEY_LAST_URL = "lastUrl";        // backendUrl the token was paired against

    const DEFAULT_BACKEND = "https://volvowatchapp.tallimedia.com";

    //! The backend base URL from settings, or the default.
    //!
    //! Only https:// is accepted — the device token travels in an Authorization
    //! header, so a plain-http (or otherwise malformed) setting would leak it.
    //! Anything else falls back to the default rather than being used.
    function backendUrl() as String {
        var url = Application.Properties.getValue("backendUrl");
        if (!(url instanceof String)) {
            return DEFAULT_BACKEND;
        }
        var s = url as String;

        // trim trailing slashes
        while (s.length() > 0) {
            var tail = s.substring(s.length() - 1, s.length());
            if (tail != null && tail.equals("/")) {
                var head = s.substring(0, s.length() - 1);
                s = (head != null) ? head : "";
            } else {
                break;
            }
        }

        if (s.length() < 9) {           // shortest plausible "https://x"
            return DEFAULT_BACKEND;
        }
        var scheme = s.substring(0, 8);
        if (scheme == null || !scheme.equals("https://")) {
            return DEFAULT_BACKEND;
        }
        return s;
    }

    function carLabel() as String {
        if (DevConfig.CAR_LABEL.length() > 0) {
            return DevConfig.CAR_LABEL;
        }
        var v = Application.Properties.getValue("carLabel");
        if (v instanceof String && (v as String).length() > 0) {
            return v as String;
        }
        return "Volvo";
    }

    function pairingCode() as String? {
        var c = Application.Properties.getValue("pairingCode");
        if (c instanceof String && (c as String).length() > 0) {
            return (c as String).toUpper();
        }
        return null;
    }

    function clearPairingCode() as Void {
        Application.Properties.setValue("pairingCode", "");
    }

    function deviceToken() as String? {
        var t = Storage.getValue(KEY_DEVICE_TOKEN);
        if (t instanceof String && (t as String).length() > 0) {
            return t as String;
        }
        if (DevConfig.DEVICE_TOKEN.length() > 0) {
            return DevConfig.DEVICE_TOKEN;
        }
        return null;
    }

    function setDeviceToken(token as String) as Void {
        Storage.setValue(KEY_DEVICE_TOKEN, token);
        Storage.setValue(KEY_LAST_URL, backendUrl());
    }

    function clearDeviceToken() as Void {
        Storage.deleteValue(KEY_DEVICE_TOKEN);
    }

    function cachedStatus() as Dictionary? {
        var s = Storage.getValue(KEY_STATUS);
        return (s instanceof Dictionary) ? (s as Dictionary) : null;
    }

    function statusAgeSeconds() as Number? {
        var t = Storage.getValue(KEY_STATUS_TIME);
        if (t instanceof Number) {
            return Time.now().value() - (t as Number);
        }
        return null;
    }

    function setStatus(status as Dictionary) as Void {
        Storage.setValue(KEY_STATUS, status);
        Storage.setValue(KEY_STATUS_TIME, Time.now().value());
    }

    //! If the backend URL was changed, the old token is meaningless.
    function onSettingsChanged() as Void {
        var last = Storage.getValue(KEY_LAST_URL);
        if (last instanceof String && !(last as String).equals(backendUrl())) {
            clearDeviceToken();
            Storage.deleteValue(KEY_STATUS);
        }
    }
}
