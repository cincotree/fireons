import pytest
from fastapi import HTTPException

import ingestion.rate_limit as rate_limit
from ingestion.rate_limit import MAX_UPLOADS_PER_WINDOW, WINDOW_SECONDS, check_rate_limit


def test_allows_up_to_the_limit():
    user_id = "rate-limit-test-user-allows"
    for _ in range(MAX_UPLOADS_PER_WINDOW):
        check_rate_limit(user_id)


def test_blocks_over_the_limit():
    user_id = "rate-limit-test-user-blocks"
    for _ in range(MAX_UPLOADS_PER_WINDOW):
        check_rate_limit(user_id)

    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit(user_id)
    assert exc_info.value.status_code == 429


def test_limits_are_independent_per_user():
    for _ in range(MAX_UPLOADS_PER_WINDOW):
        check_rate_limit("rate-limit-test-user-a")

    check_rate_limit("rate-limit-test-user-b")


def test_old_uploads_age_out_of_the_window(monkeypatch):
    user_id = "rate-limit-test-user-window"
    current_time = [0.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: current_time[0])

    for _ in range(MAX_UPLOADS_PER_WINDOW):
        check_rate_limit(user_id)
    with pytest.raises(HTTPException):
        check_rate_limit(user_id)

    current_time[0] += WINDOW_SECONDS + 1
    check_rate_limit(user_id)
