import pytest
from unittest.mock import patch

def test_first_request_is_allowed():
    from services.ratelimit import check_and_increment, _counts
    _counts.clear()
    with patch("services.ratelimit.settings") as s:
        s.rate_limit_per_day = 20
        allowed = check_and_increment("1.2.3.4")
    assert allowed is True

def test_request_blocked_after_limit():
    from services.ratelimit import check_and_increment, _counts
    _counts.clear()
    with patch("services.ratelimit.settings") as s:
        s.rate_limit_per_day = 2
        check_and_increment("5.5.5.5")
        check_and_increment("5.5.5.5")
        blocked = check_and_increment("5.5.5.5")
    assert blocked is False

def test_different_ips_are_independent():
    from services.ratelimit import check_and_increment, _counts
    _counts.clear()
    with patch("services.ratelimit.settings") as s:
        s.rate_limit_per_day = 1
        check_and_increment("10.0.0.1")
        allowed = check_and_increment("10.0.0.2")
    assert allowed is True
