import json
import logging
import time
import redis

logger = logging.getLogger(__name__)

class RedisStore:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        try:
            self.client = redis.from_url(redis_url, decode_responses=True)
            self.ping()
        except redis.ConnectionError as e:
            logger.warning(f"Failed to connect to Redis: {e}")
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
            return
        self.client.hset('targets', target_id, json.dumps(target_data))

    def get_target(self, target_id: str) -> dict | None:
        if not self.client:
            return None
        data = self.client.hget('targets', target_id)
        return json.loads(data) if data else None

    def get_all_targets(self) -> list[dict]:
        if not self.client:
            return []
        data = self.client.hgetall('targets')
        return [json.loads(val) for val in data.values()]

    def delete_target(self, target_id: str):
        if not self.client:
            return
        self.client.hdel('targets', target_id)

    def store_event(self, event_id: str, event_data: dict):
        if not self.client:
            return
        self.client.hset('events', event_id, json.dumps(event_data))

    def get_event(self, event_id: str) -> dict | None:
        if not self.client:
            return None
        data = self.client.hget('events', event_id)
        return json.loads(data) if data else None

    def store_delivery(self, event_id: str, delivery_data: dict):
        if not self.client:
            return
        key = f"deliveries:{event_id}"
        self.client.set(key, json.dumps(delivery_data), ex=86400)

    def get_deliveries(self, event_id: str) -> dict | None:
        if not self.client:
            return None
        key = f"deliveries:{event_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None

    def check_idempotency(self, key: str) -> dict | None:
        if not self.client:
            return None
        data = self.client.get(f"idempotency:{key}")
        return json.loads(data) if data else None

    def set_idempotency(self, key: str, result: dict, ttl: int = 3600):
        if not self.client:
            return
        self.client.set(f"idempotency:{key}", json.dumps(result), ex=ttl)

    def add_to_dlq(self, delivery_id: str, data: dict):
        if not self.client:
            return
        data['dlq_timestamp'] = time.time()
        self.client.hset('dlq', delivery_id, json.dumps(data))

    def get_dlq(self) -> list[dict]:
        if not self.client:
            return []
        data = self.client.hgetall('dlq')
        return [json.loads(val) for val in data.values()]

    def get_dlq_item(self, delivery_id: str) -> dict | None:
        if not self.client:
            return None
        data = self.client.hget('dlq', delivery_id)
        return json.loads(data) if data else None

    def remove_from_dlq(self, delivery_id: str):
        if not self.client:
            return
        self.client.hdel('dlq', delivery_id)

    def increment_counter(self, name: str):
        if not self.client:
            return
        self.client.incr(f"counter:{name}")

    def get_counter(self, name: str) -> int:
        if not self.client:
            return 0
        val = self.client.get(f"counter:{name}")
        return int(val) if val else 0

    def get_all_counters(self) -> dict:
        if not self.client:
            return {}
        keys = self.client.keys('counter:*')
        res = {}
        for k in keys:
            name = k.replace('counter:', '')
            val = self.client.get(k)
            res[name] = int(val) if val else 0
        return res
