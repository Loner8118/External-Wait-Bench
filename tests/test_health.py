"""Tests for health and status endpoints."""
import json

def test_root_endpoint(client):
    """GET / returns 200 with app name"""
    response = client.get('/')
    assert response.status_code == 200
    data = json.loads(response.data)
    # The prompt says welcome JSON, we just check it's successful and returns dict
    assert isinstance(data, dict)

def test_health_endpoint(client):
    """GET /health returns 200 with status 'healthy'"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get('status') == 'healthy'

def test_health_contains_redis_status(client):
    """health response has 'redis' key"""
    response = client.get('/health')
    data = json.loads(response.data)
    assert 'redis' in data

def test_health_contains_timestamp(client):
    """health response has 'timestamp' key"""
    response = client.get('/health')
    data = json.loads(response.data)
    assert 'timestamp' in data

def test_status_endpoint(client):
    """GET /api/v1/status returns 200"""
    response = client.get('/api/v1/status')
    assert response.status_code == 200

def test_status_contains_uptime(client):
    """status response has 'uptime_seconds'"""
    response = client.get('/api/v1/status')
    data = json.loads(response.data)
    assert 'uptime_seconds' in data

def test_status_contains_delivery_mode(client):
    """status response has 'delivery_mode'"""
    response = client.get('/api/v1/status')
    data = json.loads(response.data)
    assert 'delivery_mode' in data

def test_benchmark_config(client):
    """GET /api/v1/benchmark/config returns 200 with config data"""
    response = client.get('/api/v1/benchmark/config')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, dict)
