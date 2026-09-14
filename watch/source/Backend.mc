import Toybox.Communications;
import Toybox.Lang;

//! Thin wrapper over the VolvoWatch backend REST API.
//!
//! Every callback receives (ok as Boolean, payload as Dictionary or String or Null):
//!   ok == true  -> payload is the parsed JSON body (Dictionary)
//!   ok == false -> payload is a short error key (String), one of:
//!       "phone", "auth", "rate", "reconnect", "http:<code>", "net"
(:glance)
module Backend {

    typedef Cb as Method(ok as Boolean, payload as Dictionary or String or Null) as Void;

    function status(cb as Cb) as Void {
        var token = Store.deviceToken();
        if (token == null) {
            cb.invoke(false, "auth");
            return;
        }
        _get("/v1/status", token, cb);
    }

    function pair(code as String, cb as Cb) as Void {
        var options = {
            :method => Communications.HTTP_REQUEST_METHOD_POST,
            :responseType => Communications.HTTP_RESPONSE_CONTENT_TYPE_JSON,
            :headers => { "Content-Type" => Communications.REQUEST_CONTENT_TYPE_JSON }
        };
        Communications.makeWebRequest(
            Store.backendUrl() + "/v1/pair",
            { "code" => code },
            options,
            new Responder(cb).method(:onResponse)
        );
    }

    //! name: "climate-start" | "climate-stop"
    function command(name as String, cb as Cb) as Void {
        var token = Store.deviceToken();
        if (token == null) {
            cb.invoke(false, "auth");
            return;
        }
        var options = {
            :method => Communications.HTTP_REQUEST_METHOD_POST,
            :responseType => Communications.HTTP_RESPONSE_CONTENT_TYPE_JSON,
            :headers => {
                "Content-Type" => Communications.REQUEST_CONTENT_TYPE_JSON,
                "Authorization" => "Bearer " + token
            }
        };
        Communications.makeWebRequest(
            Store.backendUrl() + "/v1/command/" + name,
            {},
            options,
            new Responder(cb).method(:onResponse)
        );
    }

    function _get(path as String, token as String, cb as Cb) as Void {
        var options = {
            :method => Communications.HTTP_REQUEST_METHOD_GET,
            :responseType => Communications.HTTP_RESPONSE_CONTENT_TYPE_JSON,
            :headers => { "Authorization" => "Bearer " + token }
        };
        Communications.makeWebRequest(
            Store.backendUrl() + path,
            null,
            options,
            new Responder(cb).method(:onResponse)
        );
    }

    //! Holds the caller's callback across the async request.
    class Responder {
        private var _cb as Cb;

        function initialize(cb as Cb) {
            _cb = cb;
        }

        function onResponse(code as Number, data as Dictionary or String or Null) as Void {
            if (code == 200) {
                if (data instanceof Dictionary) {
                    _cb.invoke(true, data);
                } else {
                    _cb.invoke(false, "net");
                }
                return;
            }
            if (code == 401) {
                _cb.invoke(false, "auth");
            } else if (code == 429) {
                _cb.invoke(false, "rate");
            } else if (code == 502 || code == 503) {
                _cb.invoke(false, "reconnect");
            } else if (code == 409) {
                _cb.invoke(false, "offline");
            } else if (code == Communications.BLE_CONNECTION_UNAVAILABLE
                    || code == Communications.BLE_HOST_TIMEOUT
                    || code == -104
                    || code == -1001
                    || code == 0) {
                _cb.invoke(false, "phone");
            } else {
                _cb.invoke(false, "http:" + code.toString());
            }
        }
    }
}
