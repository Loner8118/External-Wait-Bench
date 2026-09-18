"""Pytest fixtures for External-Wait-Bench.

Provides a MockRedisStore that matches the real RedisStore API exactly,
enabling tests to run without a Redis instance.
"""

import time
import pytest


class MockRedisStore:
    """In-memory mock that mirrors the RedisStore API exactly.

    All method signatures and return types match app/redis_store.py.
    """

    def __init__(self, *args, **kwargs):
        self._targets = {}
        self._events = {}
        self._deliveries = {}
        self._idempotency = {}
        self._dlq = {}
        self._counters = {}

    def ping(self):
        return True

    # --- Targets ---
    def register_target(self, target_id, target_data):
        self._targets[target_id] = target_data

    def get_target(self, target_id):
        return self._targets.get(target_id)

    def get_all_targets(self):
        return list(self._targets.values())

    def delete_target(self, target_id):
        if target_id in self._targets:
            del self._targets[target_id]

    # --- Events ---
    def store_event(self, event_id, event_data):
        self._events[event_id] = event_data

    def get_event(self, event_id):
        return self._events.get(event_id)

    # --- Deliveries ---
    def store_delivery(self, event_id, delivery_data):
        self._deliveries[event_id] = delivery_data

    def get_deliveries(self, event_id):
        return self._deliveries.get(event_id)

    # --- Idempotency ---
    def check_idempotency(self, key):
        return self._idempotency.get(key)

    def set_idempotency(self, key, result, ttl=3600):
        self._idempotency[key] = result

    # --- DLQ ---
    def add_to_dlq(self, delivery_id, data):
        data['dlq_timestamp'] = time.time()
        self._dlq[delivery_id] = data

    def get_dlq(self):
        return list(self._dlq.values())

    def get_dlq_item(self, delivery_id):
        return self._dlq.get(delivery_id)

    def remove_from_dlq(self, delivery_id):
        if delivery_id in self._dlq:
            del self._dlq[delivery_id]

    # --- Counters ---
    def increment_counter(self, name):
        self._counters[name] = self._counters.get(name, 0) + 1

    def get_counter(self, name):
        return self._counters.get(name, 0)

    def get_all_counters(self):
        return self._counters.copy()


@pytest.fixture
def mock_store():
    """Provides a MockRedisStore with the same API as RedisStore."""
    return MockRedisStore()


@pytest.fixture
def app(mock_store):
    """Creates Flask test app with injected mock store (no Redis needed)."""
    from app import create_app

    application = create_app(store=mock_store)
    application.config['TESTING'] = True
    yield application


@pytest.fixture
def client(app):
    """Returns app.test_client()."""
    return app.test_client()


@pytest.fixture
def sample_event():
    """Returns a sample event payload for testing."""
    return {
        'event_type': 'order.created',
        'payload': {
            'order_id': 'ORD-1001',
            'amount': 2499,
        },
    }
