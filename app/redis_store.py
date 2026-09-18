import json
import logging
import time
import redis

logger = logging.getLogger(__name__)

class RedisStore:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        
        # Fallback in-memory storage
        self._targets = {}
        self._events = {}
        self._deliveries = {}
        self._idempotency = {}
        self._dlq = {}
        self._counters = {}

        self.client = redis.from_url(redis_url, decode_responses=True)
        if not self.ping():
            logger.warning("Failed to connect to Redis. Falling back to in-memory store.")
            self.client = None

    def ping(self) -> bool:
        if not self.client:
            return False
        try:
            return self.client.ping()
        except redis.ConnectionError:
            return False

    def register_target(self, target_id: str, target_data: dict):
        if not self.client:
            self._targets[target_id] = target_data
            return
        try:
            self.client.hset('targets', target_id, json.dumps(target_data))
        except redis.ConnectionError:
            self.client = None
            self._targets[target_id] = target_data

    def get_target(self, target_id: str) -> dict | None:
        if not self.client:
            return self._targets.get(target_id)
        try:
            data = self.client.hget('targets', target_id)
            return json.loads(data) if data else None
        except redis.ConnectionError:
            return self._targets.get(target_id)

    def get_all_targets(self) -> list[dict]:
        if not self.client:
            return list(self._targets.values())
        try:
            data = self.client.hgetall('targets')
            return [json.loads(val) for val in data.values()]
        except redis.ConnectionError:
            return list(self._targets.values())

    def delete_target(self, target_id: str):
        if not self.client:
            if target_id in self._targets:
                del self._targets[target_id]
            return
        try:
            self.client.hdel('targets', target_id)
        except redis.ConnectionError:
            pass

    def store_event(self, event_id: str, event_data: dict):
        if not self.client:
            self._events[event_id] = event_data
            return
        try:
            self.client.hset('events', event_id, json.dumps(event_data))
        except redis.ConnectionError:
            self._events[event_id] = event_data

    def get_event(self, event_id: str) -> dict | None:
        if not self.client:
            return self._events.get(event_id)
        try:
            data = self.client.hget('events', event_id)
            return json.loads(data) if data else None
        except redis.ConnectionError:
            return self._events.get(event_id)

    def store_delivery(self, event_id: str, delivery_data: dict):
        if not self.client:
            self._deliveries[event_id] = delivery_data
            return
        try:
            key = f"deliveries:{event_id}"
            self.client.set(key, json.dumps(delivery_data), ex=86400)
        except redis.ConnectionError:
            self._deliveries[event_id] = delivery_data

    def get_deliveries(self, event_id: str) -> dict | None:
        if not self.client:
            return self._deliveries.get(event_id)
        try:
            key = f"deliveries:{event_id}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except redis.ConnectionError:
            return self._deliveries.get(event_id)

    def check_idempotency(self, key: str) -> dict | None:
        if not self.client:
            return self._idempotency.get(key)
        try:
            data = self.client.get(f"idempotency:{key}")
            return json.loads(data) if data else None
        except redis.ConnectionError:
            return self._idempotency.get(key)

    def set_idempotency(self, key: str, result: dict, ttl: int = 3600):
        if not self.client:
            self._idempotency[key] = result
            return
        try:
            self.client.set(f"idempotency:{key}", json.dumps(result), ex=ttl)
        except redis.ConnectionError:
            self._idempotency[key] = result

    def add_to_dlq(self, delivery_id: str, data: dict):
        data['dlq_timestamp'] = time.time()
        if not self.client:
            self._dlq[delivery_id] = data
            return
        try:
            self.client.hset('dlq', delivery_id, json.dumps(data))
        except redis.ConnectionError:
            self._dlq[delivery_id] = data

    def get_dlq(self) -> list[dict]:
        if not self.client:
            return list(self._dlq.values())
        try:
            data = self.client.hgetall('dlq')
            return [json.loads(val) for val in data.values()]
        except redis.ConnectionError:
            return list(self._dlq.values())

    def get_dlq_item(self, delivery_id: str) -> dict | None:
        if not self.client:
            return self._dlq.get(delivery_id)
        try:
            data = self.client.hget('dlq', delivery_id)
            return json.loads(data) if data else None
        except redis.ConnectionError:
            return self._dlq.get(delivery_id)

    def remove_from_dlq(self, delivery_id: str):
        if not self.client:
            if delivery_id in self._dlq:
                del self._dlq[delivery_id]
            return
        try:
            self.client.hdel('dlq', delivery_id)
        except redis.ConnectionError:
            if delivery_id in self._dlq:
                del self._dlq[delivery_id]

    def increment_counter(self, name: str):
        if not self.client:
            self._counters[name] = self._counters.get(name, 0) + 1
            return
        try:
            self.client.incr(f"counter:{name}")
        except redis.ConnectionError:
            self._counters[name] = self._counters.get(name, 0) + 1

    def get_counter(self, name: str) -> int:
        if not self.client:
            return self._counters.get(name, 0)
        try:
            val = self.client.get(f"counter:{name}")
            return int(val) if val else 0
        except redis.ConnectionError:
            return self._counters.get(name, 0)

    def get_all_counters(self) -> dict:
        if not self.client:
            return self._counters.copy()
        try:
            keys = self.client.keys('counter:*')
            res = {}
            for k in keys:
                name = k.replace('counter:', '')
                val = self.client.get(k)
                res[name] = int(val) if val else 0
            return res
        except redis.ConnectionError:
            return self._counters.copy()
