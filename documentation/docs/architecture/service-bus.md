# Service Bus Architecture

dgbit uses NNG (nanomsg next generation) for inter-process communication.

## Overview

The service bus provides three communication patterns:

```
┌─────────────────────────────────────────────────────────────┐
│                       Service Bus                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Command Bus (REQ/REP)                │    │
│  │  ipc:///tmp/dgbit_cmd.ipc                           │    │
│  │  Synchronous request-reply for API calls            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Event Bus (PUB/SUB)                  │    │
│  │  ipc:///tmp/dgbit_evt.ipc                           │    │
│  │  Async event distribution to subscribers            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Job Queue (PUSH/PULL)                │    │
│  │  ipc:///tmp/dgbit_queue.ipc                         │    │
│  │  Work distribution to workers                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Command Bus (REQ/REP)

Synchronous request-reply pattern for direct API-to-worker communication.

### Use Cases

- Dispatch backtest jobs
- Request signal generation
- Query worker status

### Example

```python
from dgbit_api.infra.messaging import NNGClient

# API side (requester)
client = NNGClient("ipc:///tmp/dgbit_cmd.ipc")
await client.connect()

response = await client.send({
    "command": "run_backtest",
    "payload": {
        "symbol": "BTCUSDT",
        "limit": 1000,
    }
})

print(f"Response: {response}")
await client.close()
```

```python
from dgbit_api.infra.messaging import NNGWorker

# Worker side (replier)
worker = NNGWorker("ipc:///tmp/dgbit_cmd.ipc")
await worker.start()

while True:
    message = await worker.recv()
    
    # Process message
    result = process_command(message)
    
    await worker.send(result)
```

### Message Format

```json
{
    "command": "run_backtest",
    "job_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "payload": {
        "symbol": "BTCUSDT",
        "interval": "15",
        "limit": 1000
    }
}
```

### Response Format

```json
{
    "status": "ok",
    "job_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "result": {
        "total_trades": 15,
        "win_rate": 0.60
    }
}
```

## Event Bus (PUB/SUB)

Asynchronous publish-subscribe pattern for event distribution.

### Use Cases

- Job status updates
- Trade notifications
- Signal broadcasts
- System alerts

### Example

```python
from dgbit_services.events import EventPublisher

# Publisher
publisher = EventPublisher("ipc:///tmp/dgbit_evt.ipc")
await publisher.connect()

await publisher.publish({
    "type": "job.completed",
    "timestamp": datetime.utcnow().isoformat(),
    "payload": {
        "job_id": "550e8400",
        "status": "completed",
    }
})
```

```python
from dgbit_services.events import EventSubscriber

# Subscriber
subscriber = EventSubscriber("ipc:///tmp/dgbit_evt.ipc")
await subscriber.connect()

# Subscribe to specific topics
await subscriber.subscribe("job.*")
await subscriber.subscribe("trade.*")

async for event in subscriber:
    if event["type"] == "job.completed":
        handle_job_complete(event["payload"])
    elif event["type"] == "trade.entered":
        handle_trade_enter(event["payload"])
```

### Topic Hierarchy

```
job.created
job.started
job.completed
job.failed

trade.entered
trade.exited
trade.updated

signal.generated

system.health
system.alert
```

## Job Queue (PUSH/PULL)

Work distribution pattern for load balancing across workers.

### Use Cases

- Distribute backtest jobs
- Balance data fetching
- Parallel signal generation

### Example

```python
from dgbit_services.jobs import JobProducer

# Producer (pushes jobs)
producer = JobProducer("ipc:///tmp/dgbit_queue.ipc")
await producer.connect()

await producer.push({
    "job_type": "backtest",
    "job_uuid": "550e8400",
    "payload": {...}
})
```

```python
from dgbit_services.jobs import JobConsumer

# Consumer (pulls jobs)
consumer = JobConsumer("ipc:///tmp/dgbit_queue.ipc")
await consumer.connect()

while True:
    job = await consumer.pull()
    
    try:
        result = process_job(job)
        await mark_complete(job["job_uuid"], result)
    except Exception as e:
        await mark_failed(job["job_uuid"], str(e))
```

### Load Balancing

Multiple workers can pull from the same queue:

```
              ┌─────────────┐
              │  Producer   │
              └─────────────┘
                    │
                    ▼
              ┌─────────────┐
              │    Queue    │
              └─────────────┘
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │Worker 1 │ │Worker 2 │ │Worker 3 │
    └─────────┘ └─────────┘ └─────────┘
```

## Socket Addresses

| Socket | Address | Pattern |
|--------|---------|---------|
| Command | `ipc:///tmp/dgbit_cmd.ipc` | REQ/REP |
| Event | `ipc:///tmp/dgbit_evt.ipc` | PUB/SUB |
| Queue | `ipc:///tmp/dgbit_queue.ipc` | PUSH/PULL |
| Data | `ipc:///tmp/dgbit_data.ipc` | REQ/REP |

Configure via environment variables:

```env
NNG_COMMAND_ADDRESS=ipc:///tmp/dgbit_cmd.ipc
NNG_EVENT_ADDRESS=ipc:///tmp/dgbit_evt.ipc
NNG_JOB_QUEUE_ADDRESS=ipc:///tmp/dgbit_queue.ipc
```

## Error Handling

### Timeouts

```python
client = NNGClient(address, timeout_ms=30000)

try:
    response = await client.send(message)
except TimeoutError:
    logger.error("Request timed out")
```

### Reconnection

```python
class ResilientClient:
    async def send(self, message):
        for attempt in range(3):
            try:
                return await self.client.send(message)
            except ConnectionError:
                await asyncio.sleep(2 ** attempt)
                await self.client.connect()
        raise ConnectionError("Failed after 3 attempts")
```

### Dead Letter Queue

Handle unprocessable messages:

```python
async def process_with_dlq(job):
    try:
        return await process_job(job)
    except Exception as e:
        await dead_letter_queue.push({
            "original_job": job,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })
```

## Performance

### Throughput

| Pattern | Messages/sec |
|---------|--------------|
| REQ/REP | ~10,000 |
| PUB/SUB | ~50,000 |
| PUSH/PULL | ~30,000 |

### Latency

| Pattern | Avg Latency |
|---------|-------------|
| REQ/REP | < 1ms |
| PUB/SUB | < 0.5ms |
| PUSH/PULL | < 0.5ms |

## Best Practices

1. **Use appropriate patterns**
   - REQ/REP for queries requiring responses
   - PUB/SUB for notifications
   - PUSH/PULL for work distribution

2. **Handle failures gracefully**
   - Implement timeouts
   - Add retry logic
   - Log errors

3. **Monitor queue depth**
   - Alert on backlog
   - Scale workers as needed

4. **Message sizing**
   - Keep messages small
   - Use references for large data
