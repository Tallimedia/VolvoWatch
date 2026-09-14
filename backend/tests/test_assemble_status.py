import json
from pathlib import Path

import pytest

from app.service import assemble_status

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "xc60_probe.json").read_text())


@pytest.fixture
def status():
    return assemble_status("TESTVIN", FIXTURE)


def test_battery_and_fuel(status):
    assert status.battery_pct == 5.0
    assert status.fuel_litres == 32.4
    assert status.fuel_pct is None  # no tank size configured


def test_ranges(status):
    assert status.fuel_range_km == 270
    assert status.battery_range_km == 2
    assert status.range_km == 272


def test_charging(status):
    assert status.charging == "idle"
    assert status.charging_type == "none"


def test_trip_meters(status):
    assert status.trip_km == 317.6
    assert status.trip_auto_km == 18.4
    assert status.plugged_in is False
    # Volvo reports 0 (not absent) for this field while idle/disconnected —
    # a real value, not "unknown". See test_time_to_full_zero_is_not_masked.
    assert status.time_to_full_min == 0


def test_time_to_full_zero_is_not_masked():
    """A falsy-but-real 0 must not collapse to None (regression: it used to,
    via `int(ttf) if ttf else None`, which treats 0 the same as missing)."""
    assert FIXTURE["energy"]["estimatedChargingTimeToTargetBatteryChargeLevel"]["value"] == 0
    s = assemble_status("V", FIXTURE)
    assert s.time_to_full_min == 0


def test_plugged_in_true_for_any_non_disconnected_status():
    """Regression: `plugged_in` used to require an exact "CONNECTED" match
    against chargerConnectionStatus. Volvo's enum isn't just
    CONNECTED/DISCONNECTED (e.g. a charging-specific variant) — an exact
    match wrongly reported "unplugged" while genuinely mid-charge, even
    though the main-screen bolt icon (driven by chargingStatus) showed
    correctly. Anything other than DISCONNECTED must count as plugged in."""
    data = json.loads(json.dumps(FIXTURE))
    data["energy"]["chargerConnectionStatus"]["value"] = "CONNECTED_CHARGING"
    data["energy"]["chargingStatus"]["value"] = "CHARGING"
    s = assemble_status("V", data)
    assert s.plugged_in is True
    assert s.charging == "charging"


def test_lock_and_closed(status):
    assert status.locked is True
    assert status.all_closed is True
    assert status.doors_closed is True
    assert status.windows_closed is True


def test_service_due_from_warning(status):
    assert status.service_due is True
    assert status.service_in_km == 0
    assert status.service_in_months == 1  # unit is months, not days


def test_odometer(status):
    assert status.odometer_km == 82299


def test_car_in_use(status):
    assert status.car_reachable is False
    assert status.unreachable_reason == "CAR_IN_USE"


def test_fuel_pct_when_tank_configured(monkeypatch):
    from app import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("FUEL_TANK_LITRES", "60")
    s = assemble_status("TESTVIN", FIXTURE)
    assert s.fuel_pct == 54.0  # 32.4 / 60
    config.get_settings.cache_clear()


def test_fuel_pct_zero_is_not_masked(monkeypatch):
    """A genuinely empty tank (0.0 L) must not collapse to None (regression:
    it used to, via `if fuel_litres and tank`, which treats 0 the same as
    missing — same class of bug already fixed for time_to_full_min)."""
    from app import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("FUEL_TANK_LITRES", "60")
    data = json.loads(json.dumps(FIXTURE))
    data["fuel"]["data"]["fuelAmount"]["value"] = 0
    s = assemble_status("TESTVIN", data)
    assert s.fuel_pct == 0.0
    config.get_settings.cache_clear()


def test_service_in_months_zero_is_not_masked():
    """Service due *this month* (0) must not collapse to None (same
    falsy-vs-None class as time_to_full_min and fuel_pct above)."""
    data = json.loads(json.dumps(FIXTURE))
    data["diagnostics"]["data"]["timeToService"]["value"] = 0
    s = assemble_status("V", data)
    assert s.service_in_months == 0


def test_open_window_breaks_all_closed():
    data = json.loads(json.dumps(FIXTURE))
    data["windows"]["data"]["sunroof"]["value"] = "OPEN"
    s = assemble_status("V", data)
    assert s.all_closed is False
    assert s.windows_closed is False
    assert s.doors_closed is True  # doors are fine — only the window opened


def test_open_door_breaks_all_closed_but_not_windows():
    data = json.loads(json.dumps(FIXTURE))
    data["doors"]["data"]["frontLeftDoor"]["value"] = "OPEN"
    s = assemble_status("V", data)
    assert s.all_closed is False
    assert s.doors_closed is False
    assert s.windows_closed is True


def test_missing_payloads_are_safe():
    s = assemble_status("V", {})
    assert s.vin == "V"
    assert s.battery_pct is None
    assert s.locked is None


def test_malformed_payloads_do_not_crash():
    """Volvo returning a list/string/None where we expect an object."""
    junk = {
        "fuel": ["not", "a", "dict"],
        "energy": None,
        "statistics": "nope",
        "odometer": {"data": []},
        "doors": {"data": None},
        "windows": 42,
        "diagnostics": {},
        "command_accessibility": {"data": {"availabilityStatus": "not-a-dict"}},
    }
    s = assemble_status("V", junk)
    assert s.vin == "V"
    assert s.range_km is None
    assert s.car_reachable is None


def test_naive_timestamp_does_not_crash():
    """A timestamp without a Z/offset must not blow up the aware/naive subtraction."""
    data = json.loads(json.dumps(FIXTURE))
    data["fuel"]["data"]["fuelAmount"]["timestamp"] = "2026-09-03T19:21:23.645712"
    s = assemble_status("V", data)
    assert s.fuel_litres == 32.4


def test_non_string_timestamp_is_ignored():
    data = json.loads(json.dumps(FIXTURE))
    data["fuel"]["data"]["fuelAmount"]["timestamp"] = 12345
    assert assemble_status("V", data).vin == "V"
