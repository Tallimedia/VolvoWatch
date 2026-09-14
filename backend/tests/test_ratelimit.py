"""Regression test for the /v1/pair brute-force fix — a 6-digit pairing
code (1e6 space) had no throttling at all before this."""

from app import ratelimit


def test_allows_up_to_the_limit():
    key = "test-allow"
    for _ in range(5):
        assert ratelimit.allow(key, max_attempts=5, window_s=60) is True


def test_blocks_once_over_the_limit():
    key = "test-block"
    for _ in range(5):
        ratelimit.allow(key, max_attempts=5, window_s=60)
    assert ratelimit.allow(key, max_attempts=5, window_s=60) is False


def test_different_keys_are_independent():
    for _ in range(5):
        ratelimit.allow("key-a", max_attempts=5, window_s=60)
    # key-a is now exhausted; key-b (a different IP) must be unaffected.
    assert ratelimit.allow("key-b", max_attempts=5, window_s=60) is True


def test_old_attempts_age_out_of_the_window():
    key = "test-expiry"
    for _ in range(5):
        ratelimit.allow(key, max_attempts=5, window_s=0.01)
    assert ratelimit.allow(key, max_attempts=5, window_s=0.01) is False

    import time

    time.sleep(0.02)
    # The whole window has elapsed — this should read as a fresh start, not
    # still-blocked forever.
    assert ratelimit.allow(key, max_attempts=5, window_s=0.01) is True
