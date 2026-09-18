from app.redis_store import RedisStore

def check_idempotency(store: RedisStore, idempotency_key: str) -> tuple[bool, dict | None]:
    result = store.check_idempotency(idempotency_key)
    if result is not None:
        return True, result
    return False, None

def set_idempotency(store: RedisStore, idempotency_key: str, result: dict, ttl: int = 3600):
    store.set_idempotency(idempotency_key, result, ttl)
