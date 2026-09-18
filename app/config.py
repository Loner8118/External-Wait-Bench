import os

class Config:
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('DEBUG', 'false').lower() in ('true', '1', 't')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    DELIVERY_MODE = os.environ.get('DELIVERY_MODE', 'parallel')
    REQUEST_TIMEOUT_MS = int(os.environ.get('REQUEST_TIMEOUT_MS', 2000))
    MAX_RETRIES = int(os.environ.get('MAX_RETRIES', 3))
    RETRY_BASE_DELAY_MS = int(os.environ.get('RETRY_BASE_DELAY_MS', 100))
    IDEMPOTENCY_TTL_SECONDS = int(os.environ.get('IDEMPOTENCY_TTL_SECONDS', 3600))
    
    TARGET_A_URL = os.environ.get('TARGET_A_URL', 'http://target-a:5000')
    TARGET_B_URL = os.environ.get('TARGET_B_URL', 'http://target-b:5000')
    TARGET_C_URL = os.environ.get('TARGET_C_URL', 'http://target-c:5000')
    TARGET_D_URL = os.environ.get('TARGET_D_URL', 'http://target-d:5000')

    @classmethod
    def get_default_targets(cls) -> list[dict]:
        return [
            {'id': 'target_a', 'name': 'Target A', 'url': cls.TARGET_A_URL},
            {'id': 'target_b', 'name': 'Target B', 'url': cls.TARGET_B_URL},
            {'id': 'target_c', 'name': 'Target C', 'url': cls.TARGET_C_URL},
            {'id': 'target_d', 'name': 'Target D', 'url': cls.TARGET_D_URL},
        ]

    @classmethod
    def request_timeout_seconds(cls) -> float:
        return cls.REQUEST_TIMEOUT_MS / 1000.0

    @classmethod
    def retry_base_delay_seconds(cls) -> float:
        return cls.RETRY_BASE_DELAY_MS / 1000.0

    @classmethod
    def to_dict(cls) -> dict:
        return {
            'port': cls.PORT,
            'debug': cls.DEBUG,
            'redis_url': cls.REDIS_URL,
            'delivery_mode': cls.DELIVERY_MODE,
            'request_timeout_ms': cls.REQUEST_TIMEOUT_MS,
            'max_retries': cls.MAX_RETRIES,
            'retry_base_delay_ms': cls.RETRY_BASE_DELAY_MS,
            'idempotency_ttl_seconds': cls.IDEMPOTENCY_TTL_SECONDS
        }
