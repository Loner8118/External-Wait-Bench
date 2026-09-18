"""Tests for the DeliveryService.

Unit tests that exercise the delivery service directly (not through HTTP),
with mocked WebhookService to avoid real network calls.
"""

from unittest.mock import MagicMock
from app.delivery import DeliveryService
from app.retry import RetryHandler


def _make_success_response(latency_ms=50):
    """Helper to create a successful webhook response dict."""
    return {
        'success': True,
        'status_code': 200,
        'response_body': '{"status": "received"}',
        'latency_ms': latency_ms,
        'error': None,
    }


def _make_failure_response(error='HTTP 500', latency_ms=50):
    """Helper to create a failed webhook response dict."""
    return {
        'success': False,
        'status_code': 500,
        'response_body': '{"error": "Internal Server Error"}',
        'latency_ms': latency_ms,
        'error': error,
    }


def _make_service(mock_webhook, mock_store, mode='sequential', max_retries=0):
    """Create a DeliveryService with mocked dependencies."""
    retry_handler = RetryHandler(max_retries=max_retries, base_delay_seconds=0)
    return DeliveryService(mock_webhook, retry_handler, mock_store, mode)


def _make_targets(count=1):
    """Create a list of target dicts."""
    return [
        {'id': f'tgt_{i}', 'url': f'http://test{i}.com', 'name': f'Test {i}'}
        for i in range(count)
    ]


def test_deliver_to_single_target(mock_store):
    """Delivers to one target successfully."""
    mock_webhook = MagicMock()
    mock_webhook.send_webhook.return_value = _make_success_response()
    service = _make_service(mock_webhook, mock_store)
    targets = _make_targets(1)

    result = service.deliver_event('evt_1', {'type': 'test'}, targets)

    assert result['status'] == 'success'
    assert len(result['deliveries']) == 1
    assert result['deliveries'][0]['status'] == 'delivered'
    assert result['successful'] == 1
    assert result['failed'] == 0


def test_deliver_to_multiple_targets(mock_store):
    """Delivers to 4 targets successfully."""
    mock_webhook = MagicMock()
    mock_webhook.send_webhook.return_value = _make_success_response()
    service = _make_service(mock_webhook, mock_store)
    targets = _make_targets(4)

    result = service.deliver_event('evt_1', {'type': 'test'}, targets)

    assert result['status'] == 'success'
    assert len(result['deliveries']) == 4
    assert result['total_targets'] == 4
    assert result['successful'] == 4
    assert mock_webhook.send_webhook.call_count == 4


def test_parallel_delivery_mode(mock_store):
    """Verify parallel mode works with multiple targets."""
    mock_webhook = MagicMock()
    mock_webhook.send_webhook.return_value = _make_success_response()
    service = _make_service(mock_webhook, mock_store, mode='parallel')
    targets = _make_targets(3)

    result = service.deliver_event('evt_1', {'type': 'test'}, targets)

    assert result['status'] == 'success'
    assert len(result['deliveries']) == 3


def test_sequential_delivery_mode(mock_store):
    """Verify sequential mode works with multiple targets."""
    mock_webhook = MagicMock()
    mock_webhook.send_webhook.return_value = _make_success_response()
    service = _make_service(mock_webhook, mock_store, mode='sequential')
    targets = _make_targets(3)

    result = service.deliver_event('evt_1', {'type': 'test'}, targets)

    assert result['status'] == 'success'
    assert len(result['deliveries']) == 3


def test_delivery_records_latency(mock_store):
    """Each delivery result includes latency_ms."""
    mock_webhook = MagicMock()
    mock_webhook.send_webhook.return_value = _make_success_response(latency_ms=120)
    service = _make_service(mock_webhook, mock_store)
    targets = _make_targets(1)

    result = service.deliver_event('evt_1', {'type': 'test'}, targets)

    assert 'latency_ms' in result['deliveries'][0]


def test_partial_success(mock_store):
    """Some targets succeed, some fail — status is 'partial_success'."""
    mock_webhook = MagicMock()
    mock_webhook.send_webhook.side_effect = [
        _make_success_response(),
        _make_failure_response(),
    ]
    service = _make_service(mock_webhook, mock_store, mode='sequential')
    targets = _make_targets(2)

    result = service.deliver_event('evt_1', {'type': 'test'}, targets)

    assert result['status'] == 'partial_success'
    assert result['successful'] == 1
    assert result['failed'] == 1
    statuses = [d['status'] for d in result['deliveries']]
    assert 'delivered' in statuses
    assert 'failed' in statuses


def test_all_fail(mock_store):
    """All targets fail — status is 'failed'."""
    mock_webhook = MagicMock()
    mock_webhook.send_webhook.return_value = _make_failure_response()
    service = _make_service(mock_webhook, mock_store, mode='sequential')
    targets = _make_targets(2)

    result = service.deliver_event('evt_1', {'type': 'test'}, targets)

    assert result['status'] == 'failed'
    assert result['successful'] == 0
    assert result['failed'] == 2


def test_failed_delivery_goes_to_dlq(mock_store):
    """Failed deliveries (after all retries) are added to the DLQ."""
    mock_webhook = MagicMock()
    mock_webhook.send_webhook.return_value = _make_failure_response()
    service = _make_service(mock_webhook, mock_store)
    targets = _make_targets(1)

    service.deliver_event('evt_1', {'type': 'test'}, targets)

    dlq_items = mock_store.get_dlq()
    assert len(dlq_items) == 1


def test_delivery_increments_counters(mock_store):
    """Counters are incremented for each delivery attempt."""
    mock_webhook = MagicMock()
    mock_webhook.send_webhook.return_value = _make_success_response()
    service = _make_service(mock_webhook, mock_store)
    targets = _make_targets(2)

    service.deliver_event('evt_1', {'type': 'test'}, targets)

    assert mock_store.get_counter('events_processed') == 1
    assert mock_store.get_counter('deliveries_attempted') == 2
    assert mock_store.get_counter('deliveries_succeeded') == 2


def test_delivery_stores_results(mock_store):
    """Delivery results are stored in the store."""
    mock_webhook = MagicMock()
    mock_webhook.send_webhook.return_value = _make_success_response()
    service = _make_service(mock_webhook, mock_store)
    targets = _make_targets(1)

    service.deliver_event('evt_1', {'type': 'test'}, targets)

    stored = mock_store.get_deliveries('evt_1')
    assert stored is not None
    assert stored['event_id'] == 'evt_1'
