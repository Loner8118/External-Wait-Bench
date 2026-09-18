"""External-Wait-Bench: Webhook Delivery Platform.

A containerized webhook delivery platform designed to benchmark external I/O,
dependency latency, retries, timeouts, and fan-out behavior under increasing load.
"""

import time
import logging
from flask import Flask
from app.config import Config
from app.redis_store import RedisStore
from app.webhook_service import WebhookService
from app.retry import RetryHandler
from app.delivery import DeliveryService
from app.routes import api

logger = logging.getLogger(__name__)


def create_app(store=None):
    """Flask application factory.

    Args:
        store: Optional RedisStore instance for dependency injection.
               If None, creates one from Config.REDIS_URL.
               Pass a mock store for testing.
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    if store is None:
        store = RedisStore(Config.REDIS_URL)

    webhook_service = WebhookService(Config.request_timeout_seconds())
    retry_handler = RetryHandler(Config.MAX_RETRIES, Config.retry_base_delay_seconds())
    delivery_service = DeliveryService(
        webhook_service, retry_handler, store, Config.DELIVERY_MODE
    )

    # Register default targets from configuration
    for target in Config.get_default_targets():
        store.register_target(target['id'], target)
        logger.info(f"Registered default target: {target['id']} -> {target['url']}")

    app.config['services'] = {
        'store': store,
        'webhook_service': webhook_service,
        'retry_handler': retry_handler,
        'delivery_service': delivery_service,
        'start_time': time.time(),
    }

    app.register_blueprint(api)

    return app
