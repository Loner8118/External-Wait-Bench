import os
import time
import random
import uuid
from flask import Flask, jsonify, request

app = Flask(__name__)

# Configuration from environment variables
SERVICE_NAME = os.environ.get('SERVICE_NAME', 'mock-service')
PORT = int(os.environ.get('PORT', 5000))
LATENCY_MS = int(os.environ.get('LATENCY_MS', 100))
ERROR_RATE = float(os.environ.get('ERROR_RATE', 0.01))
TIMEOUT_RATE = float(os.environ.get('TIMEOUT_RATE', 0.0))
TIMEOUT_DURATION_MS = int(os.environ.get('TIMEOUT_DURATION_MS', 10000))

# Stats tracking
stats = {
    'requests_total': 0,
    'requests_success': 0,
    'requests_error': 0,
    'requests_timeout': 0,
    'total_latency_ms': 0
}

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'service': SERVICE_NAME,
        'status': 'running',
        'config': {
            'latency_ms': LATENCY_MS,
            'error_rate': ERROR_RATE,
            'timeout_rate': TIMEOUT_RATE
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    stats['requests_total'] += 1
    
    # Check for timeout
    if random.random() < TIMEOUT_RATE:
        stats['requests_timeout'] += 1
        time.sleep(TIMEOUT_DURATION_MS / 1000.0)
        return jsonify({'error': 'Gateway Timeout', 'service': SERVICE_NAME}), 504
        
    # Check for error
    if random.random() < ERROR_RATE:
        stats['requests_error'] += 1
        return jsonify({'error': 'Internal Server Error', 'service': SERVICE_NAME}), 500
        
    # Success path
    sleep_time = LATENCY_MS / 1000.0
    time.sleep(sleep_time)
    
    stats['requests_success'] += 1
    stats['total_latency_ms'] += LATENCY_MS
    
    return jsonify({
        'status': 'received',
        'service': SERVICE_NAME,
        'latency_ms': LATENCY_MS,
        'received_at': time.time(),
        'request_id': str(uuid.uuid4())
    }), 200

@app.route('/stats', methods=['GET'])
def get_stats():
    avg_latency = 0
    if stats['requests_success'] > 0:
        avg_latency = stats['total_latency_ms'] / stats['requests_success']
        
    return jsonify({
        'requests_total': stats['requests_total'],
        'requests_success': stats['requests_success'],
        'requests_error': stats['requests_error'],
        'requests_timeout': stats['requests_timeout'],
        'avg_latency_ms': avg_latency
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
