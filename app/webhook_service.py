import time
import requests
import logging

logger = logging.getLogger(__name__)

class WebhookService:
    def __init__(self, timeout_seconds: float = 2.0):
        self.timeout_seconds = timeout_seconds

    def send_webhook(self, target_url: str, event_data: dict) -> dict:
        start_time = time.time()
        result = {
            'success': False,
            'status_code': None,
            'response_body': None,
            'latency_ms': 0,
            'error': None
        }
        
        endpoint = f"{target_url.rstrip('/')}/webhook"
        
        try:
            response = requests.post(endpoint, json=event_data, timeout=self.timeout_seconds)
            result['status_code'] = response.status_code
            result['response_body'] = response.text[:200]  # Store first 200 chars
            if 200 <= response.status_code < 300:
                result['success'] = True
            else:
                result['error'] = f"HTTP {response.status_code}"
        except requests.Timeout:
            result['error'] = "Request timed out"
        except requests.ConnectionError:
            result['error'] = "Connection error"
        except requests.RequestException as e:
            result['error'] = str(e)
            
        result['latency_ms'] = int((time.time() - start_time) * 1000)
        return result
