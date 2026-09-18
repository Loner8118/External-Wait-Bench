import time
import random
import logging

logger = logging.getLogger(__name__)

class RetryHandler:
    def __init__(self, max_retries: int = 3, base_delay_seconds: float = 0.1):
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds

    def execute_with_retry(self, func: callable, *args, **kwargs) -> dict:
        attempts = 0
        last_result = None
        
        while attempts <= self.max_retries:
            attempts += 1
            result = func(*args, **kwargs)
            last_result = result
            
            if result.get('success', False):
                break
                
            if attempts <= self.max_retries:
                delay = self.base_delay_seconds * (2 ** (attempts - 1))
                jitter = random.uniform(0, 0.05)
                time.sleep(delay + jitter)
                
        return {
            'result': last_result,
            'attempts': attempts,
            'retries_used': attempts - 1,
            'final_success': last_result.get('success', False) if last_result else False
        }
