"""Compact response shapes sent to the watch. Keep these small — widget memory."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PairRequest(BaseModel):
    # Real codes are 6 digits (crypto.new_pairing_code); a little slack for
    # stray whitespace, nothing close to enough for a body-size DoS on this
    # unauthenticated endpoint.
    code: str = Field(max_length=16)
    label: str = Field(default="", max_length=64)


class PairResponse(BaseModel):
    device_token: str
    vin: str


class VehicleStatus(BaseModel):
    vin: str
    fuel_litres: float | None = None
    fuel_pct: float | None = None          # only if FUEL_TANK_LITRES is configured
    battery_pct: float | None = None
    fuel_range_km: float | None = None
    battery_range_km: float | None = None
    range_km: float | None = None
    charging: str | None = None            # idle | charging | done | scheduled | fault
    charging_type: str | None = None       # ac | dc | none
    charging_power_w: float | None = None   # only during an active session
    time_to_full_min: int | None = None
    plugged_in: bool | None = None
    locked: bool | None = None
    all_closed: bool | None = None         # doors + windows
    doors_closed: bool | None = None
    windows_closed: bool | None = None
    odometer_km: float | None = None
    avg_fuel_l_100: float | None = None
    trip_km: float | None = None           # driver-resettable trip meter
    trip_auto_km: float | None = None      # auto-resets on ignition off
    service_due: bool | None = None
    service_in_km: float | None = None
    service_in_months: int | None = None
    washer_fluid_low: bool | None = None
    tyre_warning: bool | None = None       # any corner reporting low; None if no data
    car_reachable: bool | None = None      # from command-accessibility
    unreachable_reason: str | None = None  # e.g. CAR_IN_USE
    updated_at: str                        # ISO 8601, when the backend fetched this
    stale: bool = False                    # Volvo data older than ~1h
    needs_reconnect: bool = False


class CommandResult(BaseModel):
    command: str
    # Volvo's invokeStatus: COMPLETED | DELIVERED | WAITING | RUNNING |
    # REJECTED | TIMEOUT | FAILED | NOT_ALLOWED | UNKNOWN | CONNECTION_FAILURE …
    invoke_status: str
    ok: bool          # invoke_status in a success set
    message: str | None = None
