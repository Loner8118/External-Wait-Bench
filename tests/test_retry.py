"""Tests for the RetryHandler.

Tests verify exponential backoff, attempt counting, and success/failure tracking.
The RetryHandler expects callables that return dicts with a 'success' boolean key.
"""

from unittest.mock import patch, MagicMock
from app.retry import RetryHandler


def test_retry_succeeds_first_try():
    """Function succeeds on first attempt — no retries needed."""
    handler = RetryHandler(max_retries=3, base_delay_seconds=0)
    mock_func = MagicMock(return_value={'success': True, 'latency_ms': 50})

    result = handler.execute_with_retry(mock_func)

    assert result['final_success'] is True
    assert result['attempts'] == 1
    assert result['retries_used'] == 0
    assert mock_func.call_count == 1


def test_retry_succeeds_after_retries():
    """Function fails twice, then succeeds on third attempt."""
    handler = RetryHandler(max_retries=3, base_delay_seconds=0)
    mock_func = MagicMock(side_effect=[
        {'success': False, 'error': 'HTTP 500'},
        {'success': False, 'error': 'HTTP 500'},
        {'success': True, 'latency_ms': 50},
    ])

    result = handler.execute_with_retry(mock_func)

    assert result['final_success'] is True
    assert result['attempts'] == 3
    assert result['retries_used'] == 2
    assert mock_func.call_count == 3


def test_retry_exhausts_all_retries():
    """Function always fails — all retries exhausted."""
    handler = RetryHandler(max_retries=3, base_delay_seconds=0)
    mock_func = MagicMock(return_value={'success': False, 'error': 'HTTP 500'})

    result = handler.execute_with_retry(mock_func)

    assert result['final_success'] is False
    assert mock_func.call_count == 4  # 1 initial + 3 retries


def test_retry_respects_max_retries():
    """With max_retries=2, total calls should be 3 (1 initial + 2 retries)."""
    handler = RetryHandler(max_retries=2, base_delay_seconds=0)
    mock_func = MagicMock(return_value={'success': False, 'error': 'timeout'})

    handler.execute_with_retry(mock_func)

    assert mock_func.call_count == 3


def test_retry_returns_attempt_count():
    """Result includes accurate 'attempts' field."""
    handler = RetryHandler(max_retries=3, base_delay_seconds=0)
    mock_func = MagicMock(side_effect=[
        {'success': False, 'error': 'fail'},
        {'success': True, 'latency_ms': 50},
    ])

    result = handler.execute_with_retry(mock_func)

    assert 'attempts' in result
    assert result['attempts'] == 2
    assert result['retries_used'] == 1


@patch('app.retry.time.sleep')
def test_retry_exponential_backoff(mock_sleep):
    """Verify delays increase exponentially between retries."""
    handler = RetryHandler(max_retries=3, base_delay_seconds=1.0)
    mock_func = MagicMock(return_value={'success': False, 'error': 'fail'})

    handler.execute_with_retry(mock_func)

    assert mock_sleep.call_count == 3
    delays = [call[0][0] for call in mock_sleep.call_args_list]
    # Exponential backoff: ~1s, ~2s, ~4s (plus small jitter 0-50ms)
    assert delays[0] < delays[1] < delays[2]
