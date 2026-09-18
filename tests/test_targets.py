"""Tests for webhook target management endpoints.

Tests cover CRUD operations for webhook targets via the API.
Default targets are registered by create_app from Config, so these tests
add, retrieve, and delete additional custom targets.
"""

import json


def test_register_target(client):
    """POST /api/v1/targets with valid body returns 201."""
    response = client.post('/api/v1/targets', json={
        'id': 'tgt_custom',
        'name': 'Custom Target',
        'url': 'http://custom-target:8080',
    })
    assert response.status_code == 201


def test_register_target_missing_fields(client):
    """Returns 400 when required fields are missing."""
    response = client.post('/api/v1/targets', json={'id': 'tgt_1'})
    assert response.status_code == 400


def test_register_target_missing_url(client):
    """Returns 400 when url is missing."""
    response = client.post('/api/v1/targets', json={
        'id': 'tgt_1',
        'name': 'Test',
    })
    assert response.status_code == 400


def test_list_targets(client):
    """GET /api/v1/targets returns a list including default targets."""
    response = client.get('/api/v1/targets')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    # At least 4 default targets from Config
    assert len(data) >= 4


def test_list_targets_includes_registered(client):
    """Newly registered targets appear in the list."""
    client.post('/api/v1/targets', json={
        'id': 'tgt_new', 'name': 'New Target', 'url': 'http://new:5000',
    })

    response = client.get('/api/v1/targets')
    data = json.loads(response.data)
    target_ids = [t['id'] for t in data]
    assert 'tgt_new' in target_ids


def test_get_target(client):
    """GET /api/v1/targets/<id> returns a registered target."""
    client.post('/api/v1/targets', json={
        'id': 'tgt_lookup', 'name': 'Lookup Target', 'url': 'http://lookup:5000',
    })

    response = client.get('/api/v1/targets/tgt_lookup')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == 'tgt_lookup'
    assert data['name'] == 'Lookup Target'


def test_get_target_default(client):
    """Can retrieve a default target registered at startup."""
    response = client.get('/api/v1/targets/target_a')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == 'target_a'


def test_get_target_not_found(client):
    """Returns 404 for non-existent target."""
    response = client.get('/api/v1/targets/tgt_nonexistent')
    assert response.status_code == 404


def test_delete_target(client):
    """DELETE removes a target and it becomes inaccessible."""
    client.post('/api/v1/targets', json={
        'id': 'tgt_delete_me', 'name': 'Delete Me', 'url': 'http://delete:5000',
    })

    response = client.delete('/api/v1/targets/tgt_delete_me')
    assert response.status_code == 200

    # Verify it's gone
    response = client.get('/api/v1/targets/tgt_delete_me')
    assert response.status_code == 404


def test_delete_target_not_found(client):
    """Returns 404 when deleting a non-existent target."""
    response = client.delete('/api/v1/targets/tgt_nonexistent')
    assert response.status_code == 404
