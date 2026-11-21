import pytest
from fastapi import HTTPException

import ingestion.rate_limit as rate_limit
from ingestion.rate_limit import (
    MAX_CUMULATIVE_BYTES_PER_WINDOW,
    MAX_UPLOADS_PER_WINDOW,
    WINDOW_SECONDS,
    check_rate_limit,
)

ONE_MB = 1024 * 1024


def test_allows_a_realistic_bulk_upload_batch():
    user_id = "rate-limit-test-user-bulk"
    for _ in range(20):
        check_rate_limit(user_id, 2 * ONE_MB)


def test_blocks_when_cumulative_bytes_exceed_the_cap():
    user_id = "rate-limit-test-user-bytes"
    for _ in range(10):
        check_rate_limit(user_id, MAX_CUMULATIVE_BYTES_PER_WINDOW // 10)

    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit(user_id, 1)
    assert exc_info.value.status_code == 429


def test_blocks_over_the_request_count_backstop():
    user_id = "rate-limit-test-user-count"
    for _ in range(MAX_UPLOADS_PER_WINDOW):
        check_rate_limit(user_id, 1)

    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit(user_id, 1)
    assert exc_info.value.status_code == 429


def test_limits_are_independent_per_user():
    check_rate_limit("rate-limit-test-user-a", MAX_CUMULATIVE_BYTES_PER_WINDOW)

    check_rate_limit("rate-limit-test-user-b", 1)


def test_old_uploads_age_out_of_the_window(monkeypatch):
    user_id = "rate-limit-test-user-window"
    current_time = [0.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: current_time[0])

    check_rate_limit(user_id, MAX_CUMULATIVE_BYTES_PER_WINDOW)
    with pytest.raises(HTTPException):
        check_rate_limit(user_id, 1)

    current_time[0] += WINDOW_SECONDS + 1
    check_rate_limit(user_id, MAX_CUMULATIVE_BYTES_PER_WINDOW)
