import time
import uuid
import concurrent.futures
from app.webhook_service import WebhookService
from app.retry import RetryHandler
from app.redis_store import RedisStore

class DeliveryService:
    def __init__(self, webhook_service: WebhookService, retry_handler: RetryHandler, store: RedisStore, delivery_mode: str = 'parallel'):
        self.webhook_service = webhook_service
        self.retry_handler = retry_handler
        self.store = store
        self.delivery_mode = delivery_mode

    def deliver_single(self, target: dict, event_data: dict) -> dict:
        delivery_id = str(uuid.uuid4())
        retry_result = self.retry_handler.execute_with_retry(
            self.webhook_service.send_webhook, target['url'], event_data
        )
        
        res = retry_result['result']
        status = 'delivered' if retry_result['final_success'] else 'failed'
        
        return {
            'delivery_id': delivery_id,
            'target_id': target['id'],
            'target_name': target.get('name', 'Unknown'),
            'status': status,
            'latency_ms': res.get('latency_ms', 0),
            'attempts': retry_result['attempts'],
            'error': res.get('error')
        }

    def deliver_event(self, event_id: str, event_data: dict, targets: list[dict]) -> dict:
        start_time = time.time()
        self.store.increment_counter('events_processed')
        
        deliveries = []
        if self.delivery_mode == 'parallel' and targets:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(targets)) as executor:
                futures = {executor.submit(self.deliver_single, t, event_data): t for t in targets}
                for future in concurrent.futures.as_completed(futures):
                    deliveries.append(future.result())
        else:
            for target in targets:
                deliveries.append(self.deliver_single(target, event_data))
                
        successful_count = 0
        failed_count = 0
        
        for d in deliveries:
            self.store.increment_counter('deliveries_attempted')
            if d['status'] == 'delivered':
                successful_count += 1
                self.store.increment_counter('deliveries_succeeded')
            else:
                failed_count += 1
                self.store.increment_counter('deliveries_failed')
                d['event_id'] = event_id
                d['event_data'] = event_data
                self.store.add_to_dlq(d['delivery_id'], d)
                
        total_targets = len(targets)
        if total_targets == 0:
            status = 'success'
        elif successful_count == total_targets:
            status = 'success'
        elif failed_count == total_targets:
            status = 'failed'
        else:
            status = 'partial_success'
            
        summary = {
            'event_id': event_id,
            'status': status,
            'total_targets': total_targets,
            'successful': successful_count,
            'failed': failed_count,
            'deliveries': deliveries,
            'total_latency_ms': int((time.time() - start_time) * 1000)
        }
        
        self.store.store_delivery(event_id, summary)
        return summary
