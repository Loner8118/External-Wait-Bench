import uuid
import time
from flask import Blueprint, request, jsonify, current_app
from app.idempotency import check_idempotency, set_idempotency

api = Blueprint('api', __name__)

def get_services():
    return {
        'store': current_app.config['services']['store'],
        'delivery_service': current_app.config['services']['delivery_service'],
        'webhook_service': current_app.config['services']['webhook_service'],
        'retry_handler': current_app.config['services']['retry_handler'],
        'start_time': current_app.config['services']['start_time']
    }

@api.route('/', methods=['GET'])
def welcome():
    return jsonify({
        'app': 'External-Wait-Bench Webhook Delivery Platform',
        'version': '1.0.0',
        'links': {'health': '/health', 'status': '/api/v1/status'}
    })

@api.route('/health', methods=['GET'])
def health():
    store = get_services()['store']
    return jsonify({
        'status': 'healthy',
        'redis': store.ping(),
        'timestamp': time.time()
    })

@api.route('/api/v1/status', methods=['GET'])
def status():
    services = get_services()
    store = services['store']
    uptime = time.time() - services['start_time']
    return jsonify({
        'status': 'running',
        'uptime_seconds': int(uptime),
        'counters': store.get_all_counters(),
        'delivery_mode': current_app.config['DELIVERY_MODE'],
        'registered_targets': len(store.get_all_targets())
    })

@api.route('/api/v1/events', methods=['POST'])
def receive_event():
    data = request.json
    if not data or 'event_type' not in data or 'payload' not in data:
        return jsonify({'error': 'Missing event_type or payload'}), 400
        
    idempotency_key = request.headers.get('Idempotency-Key')
    services = get_services()
    store = services['store']
    
    if idempotency_key:
        is_cached, cached_result = check_idempotency(store, idempotency_key)
        if is_cached:
            return jsonify(cached_result), 200
            
    event_id = f"evt_{str(uuid.uuid4())[:8]}"
    store.store_event(event_id, data)
    
    targets = store.get_all_targets()
    delivery_service = services['delivery_service']
    summary = delivery_service.deliver_event(event_id, data, targets)
    
    if idempotency_key:
        set_idempotency(store, idempotency_key, summary, current_app.config['IDEMPOTENCY_TTL_SECONDS'])
        
    return jsonify(summary), 201

@api.route('/api/v1/events/<event_id>', methods=['GET'])
def get_event(event_id):
    store = get_services()['store']
    event = store.get_event(event_id)
    if not event:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(event)

@api.route('/api/v1/targets', methods=['POST'])
def add_target():
    data = request.json
    if not data or 'id' not in data or 'url' not in data or 'name' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    store = get_services()['store']
    store.register_target(data['id'], data)
    return jsonify({'message': 'Target registered'}), 201

@api.route('/api/v1/targets', methods=['GET'])
def list_targets():
    store = get_services()['store']
    return jsonify(store.get_all_targets())

@api.route('/api/v1/targets/<target_id>', methods=['GET'])
def get_target(target_id):
    store = get_services()['store']
    target = store.get_target(target_id)
    if not target:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(target)

@api.route('/api/v1/targets/<target_id>', methods=['DELETE'])
def delete_target(target_id):
    store = get_services()['store']
    if not store.get_target(target_id):
        return jsonify({'error': 'Not found'}), 404
    store.delete_target(target_id)
    return jsonify({'message': 'Deleted'})

@api.route('/api/v1/deliveries/<event_id>', methods=['GET'])
def get_deliveries(event_id):
    store = get_services()['store']
    deliveries = store.get_deliveries(event_id)
    if not deliveries:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(deliveries)

@api.route('/api/v1/deliveries/<delivery_id>/retry', methods=['POST'])
def retry_delivery_post(delivery_id):
    return retry_dlq(delivery_id)

@api.route('/api/v1/dlq', methods=['GET'])
def get_dlq():
    store = get_services()['store']
    return jsonify(store.get_dlq())

@api.route('/api/v1/dlq/<delivery_id>/retry', methods=['POST'])
def retry_dlq(delivery_id):
    services = get_services()
    store = services['store']
    item = store.get_dlq_item(delivery_id)
    if not item:
        return jsonify({'error': 'Not found'}), 404
        
    target = store.get_target(item['target_id'])
    if not target:
        target = {'id': item['target_id'], 'url': 'unknown', 'name': item.get('target_name')}
        
    delivery_service = services['delivery_service']
    store.remove_from_dlq(delivery_id)
    result = delivery_service.deliver_single(target, item.get('event_data', {}))
    return jsonify(result), 200

@api.route('/api/v1/benchmark/config', methods=['GET'])
def get_config():
    from app.config import Config
    return jsonify(Config.to_dict())
