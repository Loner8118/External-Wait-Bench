"""Tests for event API endpoints.

Integration tests that go through the full HTTP request flow.
WebhookService HTTP calls are mocked to avoid real network requests.
"""

import json
from unittest.mock import patch, MagicMock


def _mock_successful_post():
    """Create a mock requests.post response for successful webhook delivery."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"status": "received", "service": "mock"}'
    return mock_response


@patch('app.webhook_service.requests.post')
def test_create_event_success(mock_post, client, sample_event):
    """POST /api/v1/events with valid body returns 201."""
    mock_post.return_value = _mock_successful_post()

    response = client.post('/api/v1/events', json=sample_event)

    assert response.status_code == 201


def test_create_event_missing_event_type(client):
    """Returns 400 when event_type is missing."""
    response = client.post('/api/v1/events', json={'payload': {}})
    assert response.status_code == 400


def test_create_event_missing_payload(client):
    """Returns 400 when payload is missing."""
    response = client.post('/api/v1/events', json={'event_type': 'test'})
    assert response.status_code == 400


def test_create_event_empty_body(client):
    """Returns 400 for empty request body."""
    response = client.post('/api/v1/events', json={})
    assert response.status_code == 400


@patch('app.webhook_service.requests.post')
def test_create_event_returns_event_id(mock_post, client, sample_event):
    """Response includes an event_id starting with 'evt_'."""
    mock_post.return_value = _mock_successful_post()

    response = client.post('/api/v1/events', json=sample_event)
    data = json.loads(response.data)

    assert 'event_id' in data
    assert data['event_id'].startswith('evt_')


@patch('app.webhook_service.requests.post')
def test_create_event_returns_deliveries(mock_post, client, sample_event):
    """Response includes a 'deliveries' list."""
    mock_post.return_value = _mock_successful_post()

    response = client.post('/api/v1/events', json=sample_event)
    data = json.loads(response.data)

    assert 'deliveries' in data
    assert isinstance(data['deliveries'], list)


@patch('app.webhook_service.requests.post')
def test_create_event_returns_status(mock_post, client, sample_event):
    """Response includes overall delivery status."""
    mock_post.return_value = _mock_successful_post()

    response = client.post('/api/v1/events', json=sample_event)
    data = json.loads(response.data)

    assert 'status' in data
    assert data['status'] in ('success', 'partial_success', 'failed')


@patch('app.webhook_service.requests.post')
def test_create_event_idempotency(mock_post, client, sample_event):
    """Same Idempotency-Key returns cached result on second request."""
    mock_post.return_value = _mock_successful_post()
    headers = {'Idempotency-Key': 'idem-test-123'}

    # First request — creates the event
    resp1 = client.post('/api/v1/events', json=sample_event, headers=headers)
    assert resp1.status_code == 201
    data1 = json.loads(resp1.data)

    # Second request — returns cached result (200, not 201)
    resp2 = client.post('/api/v1/events', json=sample_event, headers=headers)
    assert resp2.status_code == 200
    data2 = json.loads(resp2.data)

    assert data1['event_id'] == data2['event_id']


@patch('app.webhook_service.requests.post')
def test_get_event_success(mock_post, client, sample_event):
    """GET /api/v1/events/<id> returns the stored event data."""
    mock_post.return_value = _mock_successful_post()

    # Create an event first
    resp = client.post('/api/v1/events', json=sample_event)
    event_id = json.loads(resp.data)['event_id']

    # Retrieve it
    response = client.get(f'/api/v1/events/{event_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['event_type'] == 'order.created'


def test_get_event_not_found(client):
    """Returns 404 for non-existent event."""
    response = client.get('/api/v1/events/evt_nonexistent')
    assert response.status_code == 404
