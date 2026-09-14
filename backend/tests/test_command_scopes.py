"""Regression test for the /v1/command scope-enforcement gap — previously
only a name allowlist, no check that the backend's configured VOLVO_SCOPES
actually covers a Release-2 command (lock/unlock/flash/honk) before sending
it to Volvo.

Checks the *server's* configured scope list, not User.scopes — Volvo's
token response omits `scope` whenever it matches what was requested (the
normal case), so User.scopes is never actually populated in practice
(confirmed against real production data 2026-09-13: both existing users
have an empty User.scopes despite default-scope commands already working).
See the has_command_scope() docstring in app/volvo.py for the full story.
"""

import pytest
from pydantic import ValidationError

from app.schemas import PairRequest
from app.volvo import has_command_scope

# What production actually configures (backend/DEPLOY.md / .env) — the real
# shape has_command_scope needs to work against, not a hypothetical.
REAL_CONFIGURED_SCOPES = (
    "openid conve:fuel_status conve:battery_charge_level conve:odometer_status "
    "conve:doors_status conve:windows_status conve:lock_status "
    "conve:diagnostics_engine_status conve:diagnostics_workshop "
    "conve:climatization_start_stop conve:commands conve:command_accessibility "
    "conve:trip_statistics conve:vehicle_relation conve:warnings conve:tyre_status "
    "conve:engine_status energy:state:read energy:capability:read"
)


def test_default_scope_command_allowed_with_real_config():
    # climate-start/-stop's scope IS part of the real, currently-deployed
    # default scope list — must not be blocked under normal configuration.
    assert has_command_scope(REAL_CONFIGURED_SCOPES, "climate-start") is True
    assert has_command_scope(REAL_CONFIGURED_SCOPES, "climate-stop") is True


def test_restricted_commands_blocked_under_the_real_current_config():
    # None of Release 2's restricted scopes are in VOLVO_SCOPES yet — every
    # one of these must stay blocked until that changes.
    for cmd in ("lock", "unlock", "flash", "honk", "honk-flash"):
        assert has_command_scope(REAL_CONFIGURED_SCOPES, cmd) is False


def test_a_genuinely_empty_config_blocks_everything_scoped():
    # Not a real-world case (VOLVO_SCOPES is never actually empty in
    # deployment), but the safe behavior if it ever were is to block, not
    # silently allow.
    assert has_command_scope("", "climate-start") is False
    assert has_command_scope(None, "climate-start") is False


def test_restricted_command_allowed_once_its_scope_is_added():
    # The Release 2 rollout scenario: VOLVO_SCOPES gets the restricted
    # scopes appended, matching CHANGELOG.md's documented plan.
    granted = REAL_CONFIGURED_SCOPES + " conve:lock conve:unlock conve:honk_flash"
    assert has_command_scope(granted, "lock") is True
    assert has_command_scope(granted, "unlock") is True
    assert has_command_scope(granted, "honk") is True
    assert has_command_scope(granted, "honk-flash") is True


def test_unknown_command_name_is_not_this_functions_job():
    # command() in watch_routes.py already 404s unknown names before this
    # runs; has_command_scope just shouldn't crash on one.
    assert has_command_scope(REAL_CONFIGURED_SCOPES, "not-a-real-command") is True


def test_pair_request_rejects_oversized_code():
    with pytest.raises(ValidationError):
        PairRequest(code="1" * 1000)


def test_pair_request_accepts_a_real_code():
    assert PairRequest(code="123456").code == "123456"
