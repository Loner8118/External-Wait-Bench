"""Tests for Dead-Letter Queue (DLQ) endpoints.

Tests cover listing DLQ items and retrying failed deliveries.
"""

import json
from unittest.mock import patch, MagicMock


def test_get_dlq_empty(client):
    """GET /api/v1/dlq returns empty list when no failures exist."""
    response = client.get('/api/v1/dlq')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_dlq_with_items(client, mock_store):
    """GET /api/v1/dlq returns DLQ items after adding them."""
    mock_store.add_to_dlq('del_1', {
        'delivery_id': 'del_1',
        'target_id': 'target_a',
        'target_name': 'Target A',
        'status': 'failed',
        'error': 'HTTP 500',
        'event_data': {'event_type': 'test'},
    })

    response = client.get('/api/v1/dlq')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['status'] == 'failed'


def test_get_dlq_multiple_items(client, mock_store):
    """Multiple DLQ items are returned."""
    for i in range(3):
        mock_store.add_to_dlq(f'del_{i}', {
            'delivery_id': f'del_{i}',
            'target_id': f'tgt_{i}',
            'status': 'failed',
            'event_data': {},
        })

    response = client.get('/api/v1/dlq')
    data = json.loads(response.data)
    assert len(data) == 3


@patch('app.webhook_service.requests.post')
def test_retry_dlq_item(mock_post, client, mock_store):
    """POST /api/v1/dlq/<id>/retry removes item from DLQ and retries delivery."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"status": "received"}'
    mock_post.return_value = mock_response

    # Add a failed delivery to DLQ
    mock_store.add_to_dlq('del_retry', {
        'delivery_id': 'del_retry',
        'target_id': 'target_a',
        'target_name': 'Target A',
        'status': 'failed',
        'error': 'HTTP 500',
        'event_data': {'event_type': 'order.created', 'payload': {}},
    })

    response = client.post('/api/v1/dlq/del_retry/retry')
    assert response.status_code == 200

    # Verify item is removed from DLQ
    assert mock_store.get_dlq_item('del_retry') is None


def test_retry_dlq_item_not_found(client):
    """Returns 404 when retrying a non-existent DLQ item."""
    response = client.post('/api/v1/dlq/del_nonexistent/retry')
    assert response.status_code == 404
