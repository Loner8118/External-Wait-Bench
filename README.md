# External-Wait-Bench

*A containerized webhook delivery platform designed to benchmark external I/O, dependency latency, retries, timeouts, and fan-out behavior under increasing load.*

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=flat&logo=flask&logoColor=white)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=flat&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)

## Overview

**External-Wait-Bench** is a webhook delivery gateway that receives incoming events and fans them out to multiple downstream webhook targets. 

It exists as a **benchmark application** specifically designed for measuring and modeling external I/O waiting patterns. As part of a Final Year Project for a Performance Predictor system, this application generates purely I/O-bound workloads. 

**Key Insight**: In this application, the dominant work is *waiting* for external responses, not CPU computation or heavy database queries. It serves as a perfect testbed for observing how external dependency latency and unreliability impact system throughput and queuing behavior.

## Architecture

```text
                                +-------------------+
                                |                   |
                                |   Mock Target A   | (:5001)
                                |                   |
                                +---------^---------+
                                          |
                                +---------v---------+
+---------------+               |                   |
|               |  Event Push   |   Mock Target B   | (:5002)
| Locust Load   +--------------->                   |
| Tester        |               +---------^---------+
|               |  (HTTP POST)            |
+---------------+               +---------v---------+
                                |                   |
                                |  Webhook Gateway  | <-----> Redis (:6379)
                                |     (:5000)       |         (State, Retry, DLQ)
                                |                   |
                                +---------^---------+
                                          |
                                +---------v---------+
                                |                   |
                                |   Mock Target C   | (:5003)
                                |                   |
                                +---------^---------+
                                          |
                                +---------v---------+
                                |                   |
                                |   Mock Target D   | (:5004)
                                |                   |
                                +-------------------+
```

The gateway receives events, stores state in Redis, and fans out HTTP POST requests to configured targets. Failed deliveries are retried with exponential backoff and eventually moved to a Dead-Letter Queue (DLQ).

## Features

- **Event Ingestion & Fan-Out:** Receive a single event and fan it out to multiple downstream APIs.
- **Delivery Modes:** Support for both parallel (async) and sequential delivery modes.
- **Configurable Mock Services:** Mock downstream targets with customizable latency, error rates, and timeout rates.
- **Resilience:** Built-in retry mechanism with exponential backoff and jitter.
- **Dead-Letter Queue (DLQ):** Permanent failures are routed to a DLQ for inspection and manual retry.
- **Idempotency:** Support for `Idempotency-Key` headers to safely handle duplicate ingestion.
- **Lightweight State:** Redis-backed state management for tracking deliveries and metrics.
- **Pure I/O Benchmark:** No traditional database—designed to explicitly benchmark external I/O waits.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/External-Wait-Bench.git
cd External-Wait-Bench

# Start the application and mock targets via Docker Compose
docker compose up --build
```

### Example Usage

Create an event to fan out to the default targets:

```bash
curl -X POST http://localhost:5000/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{"type": "user.created", "payload": {"user_id": "123", "name": "Test User"}}'
```

Check the status of the gateway:

```bash
curl http://localhost:5000/api/v1/status
```

## API Reference

### GET `/`
Returns basic API information.

**Response Example:**
```json
{
  "name": "External-Wait-Bench API",
  "version": "1.0",
  "status": "online"
}
```

### GET `/health`
Health check endpoint.

**Response Example:**
```json
{
  "status": "healthy",
  "redis_connected": true
}
```

### GET `/api/v1/status`
Returns gateway status and aggregated metrics.

**Response Example:**
```json
{
  "events_processed": 150,
  "active_deliveries": 12,
  "dlq_size": 3,
  "uptime_seconds": 3600
}
```

### POST `/api/v1/events`
Ingest a new event and fan it out to configured targets.

**Request Body:**
```json
{
  "type": "order.completed",
  "payload": {
    "order_id": "9876",
    "amount": 29.99
  }
}
```

**Response Example:**
```json
{
  "event_id": "evt_8f7d6e5c4b3a",
  "status": "accepted",
  "deliveries": ["del_1", "del_2"]
}
```

### GET `/api/v1/events/{event_id}`
Get details and delivery status for a specific event.

**Response Example:**
```json
{
  "event_id": "evt_8f7d6e5c4b3a",
  "payload": {"order_id": "9876", "amount": 29.99},
  "deliveries_status": {
    "del_1": "success",
    "del_2": "pending_retry"
  }
}
```

### POST `/api/v1/targets`
Register a new webhook target.

**Request Body:**
```json
{
  "name": "Audit Service",
  "url": "http://mock-target-a:5001/webhook",
  "timeout_ms": 2000
}
```

### GET `/api/v1/targets`
List all configured webhook targets.

### GET `/api/v1/targets/{target_id}`
Get details for a specific target.

### DELETE `/api/v1/targets/{target_id}`
Remove a webhook target.

### GET `/api/v1/deliveries/{event_id}`
List all deliveries associated with a specific event.

### POST `/api/v1/deliveries/{delivery_id}/retry`
Manually retry a specific delivery.

### GET `/api/v1/dlq`
List all items in the Dead-Letter Queue.

### POST `/api/v1/dlq/{delivery_id}/retry`
Retry a specific delivery from the DLQ.

### GET `/api/v1/benchmark/config`
View the current benchmark configuration.

## Configuration

| Environment Variable | Description | Default Value |
|----------------------|-------------|---------------|
| `REDIS_URL` | Connection string for Redis | `redis://localhost:6379/0` |
| `DELIVERY_MODE` | `parallel` or `sequential` | `parallel` |
| `MAX_RETRIES` | Maximum number of delivery retries | `3` |
| `RETRY_BACKOFF_MS` | Base backoff time for retries in ms | `1000` |
| `PORT` | Port for the webhook gateway | `5000` |
| `LOG_LEVEL` | Logging level (INFO, DEBUG) | `INFO` |

## Mock Services

To facilitate accurate benchmarking without relying on real external services, this project includes configurable mock downstream targets. 

These mock services can be configured to simulate various external dependency behaviors:
- **Latency**: Introduce artificial delay (e.g., constant, random, or distribution-based).
- **Error Rate**: Return 5xx or 4xx HTTP status codes randomly.
- **Timeout Rate**: Simply drop connections or delay beyond the client timeout window.

**Default Configurations:**
- **Target A (:5001)**: 100ms latency, 1% error rate
- **Target B (:5002)**: 300ms latency, 3% error rate
- **Target C (:5003)**: 500ms latency, 5% error rate
- **Target D (:5004)**: 800ms latency, 10% error rate

You can customize these via environment variables for each target container in `docker-compose.yml`.

## Benchmark Scenarios

The following scenarios are designed to observe system behavior under various I/O constraints.

1. **Baseline**: 50ms latency, 0% errors, parallel delivery. (Establishes baseline overhead).
2. **Moderate I/O**: 100-300ms latency, 0% errors, parallel.
3. **Heavy I/O**: 300-800ms latency, 0% errors, parallel. (Tests connection pooling and async worker saturation).
4. **Sequential**: 100-800ms latency, 0% errors, sequential delivery. (Simulates strict dependency chains).
5. **Unreliable Dependency**: 300-800ms latency, 5% errors, 2% timeouts. (Tests retry queues and DLQ buildup).
6. **Retry Amplification**: 500ms latency, 10% failures, 3 retries. (Demonstrates how retries multiply backend load).

**Performance Predictor Expectation**: The predictor should successfully identify that throughput is bounded by external I/O waits and concurrency limits, rather than CPU.

## Expected Performance Characteristics

- **Low CPU Utilization**: Even under high request volume, CPU usage should remain relatively low.
- **I/O Dominated Response Time**: Gateway response times closely track the latency of the slowest downstream dependency (in parallel mode) or the sum of latencies (in sequential mode).
- **Concurrency Bottlenecks**: Throughput is primarily limited by the connection pool size, thread/worker count, and network socket limits, rather than CPU cycles.
- **Latency Scaling**: As external latency increases, overall system response time increases linearly, but CPU usage remains stable.

## Project Structure

```text
External-Wait-Bench/
├── app/                      # Webhook Gateway Application
│   ├── main.py               # Flask application factory and entry point
│   ├── api/                  # API routes (events, targets, dlq)
│   ├── services/             # Core business logic (delivery, retry)
│   ├── models/               # Data structures
│   └── utils/                # Helpers (redis client, config)
├── mock_targets/             # Mock Downstream Services
│   ├── server.py             # Configurable latency/error server
│   └── requirements.txt      
├── tests/                    # Unit and integration tests
├── load_tests/               # Locust load testing scripts
├── docker-compose.yml        # Multi-container orchestration
├── Dockerfile                # Gateway Docker image definition
├── requirements.txt          # Gateway dependencies
└── README.md                 # Project documentation
```

## Development

### Local Setup (Without Docker)

1. Ensure Redis is running locally (`redis-server`).
2. Create a virtual environment: `python -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the gateway: `flask run --port 5000`

### Running Tests
Execute the test suite using pytest:
```bash
pytest tests/
```

### Running with Docker Compose
The recommended way to run the full stack (Gateway + Redis + 4 Mock Targets):
```bash
docker compose up --build
```

## Performance Models

This benchmark is ideal for validating the following mathematical performance models:

- **Little's Law (L = λW)**: Validating the relationship between concurrency (L), throughput (λ), and external response time (W).
- **Queueing Theory**: Observing M/M/c queuing behaviors when worker pools are saturated by slow external I/O.
- **Universal Scalability Law (USL)**: Demonstrating scalability bounds dictated by external coherence/contention rather than internal limits.
- **Bottleneck Analysis**: Proving that external dependencies act as the primary system bottleneck.

## License

MIT License
