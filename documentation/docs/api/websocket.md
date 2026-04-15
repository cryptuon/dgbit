# WebSocket Reference

Real-time event streaming via WebSocket connections.

## Connection

### Event Stream

Connect to the main event stream:

```
ws://localhost:8000/api/ws/events
```

### Job-Specific Stream

Connect to updates for a specific job:

```
ws://localhost:8000/api/ws/jobs/{job_uuid}
```

## Event Format

All events follow this format:

```json
{
    "type": "event.type",
    "timestamp": "2024-01-15T10:30:00Z",
    "payload": { ... }
}
```

## Event Types

### Job Events

#### job.created

Emitted when a new job is created.

```json
{
    "type": "job.created",
    "timestamp": "2024-01-15T10:30:00Z",
    "payload": {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "job_type": "backtest",
        "status": "pending"
    }
}
```

#### job.started

Emitted when a job starts processing.

```json
{
    "type": "job.started",
    "timestamp": "2024-01-15T10:30:01Z",
    "payload": {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "job_type": "backtest",
        "status": "running"
    }
}
```

#### job.completed

Emitted when a job completes successfully.

```json
{
    "type": "job.completed",
    "timestamp": "2024-01-15T10:30:45Z",
    "payload": {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "job_type": "backtest",
        "status": "completed",
        "result": {
            "total_trades": 15,
            "win_rate": 0.60,
            "total_return": 0.12
        }
    }
}
```

#### job.failed

Emitted when a job fails.

```json
{
    "type": "job.failed",
    "timestamp": "2024-01-15T10:30:45Z",
    "payload": {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "job_type": "backtest",
        "status": "failed",
        "error": "Insufficient data for backtest"
    }
}
```

### Trade Events

#### trade.entered

Emitted when a position is opened.

```json
{
    "type": "trade.entered",
    "timestamp": "2024-01-15T10:30:00Z",
    "payload": {
        "symbol": "BTCUSDT",
        "side": "long",
        "quantity": 0.001,
        "entry_price": 42150.00,
        "take_profit": 42993.00,
        "stop_loss": 41728.50,
        "strategy": "wavelet_reversal"
    }
}
```

#### trade.exited

Emitted when a position is closed.

```json
{
    "type": "trade.exited",
    "timestamp": "2024-01-15T11:15:00Z",
    "payload": {
        "symbol": "BTCUSDT",
        "side": "long",
        "quantity": 0.001,
        "entry_price": 42150.00,
        "exit_price": 42993.00,
        "exit_type": "take_profit",
        "pnl": 0.843,
        "pnl_pct": 2.0,
        "duration_minutes": 45
    }
}
```

### Signal Events

#### signal.generated

Emitted when a strategy generates a signal.

```json
{
    "type": "signal.generated",
    "timestamp": "2024-01-15T10:30:00Z",
    "payload": {
        "strategy": "wavelet_reversal",
        "symbol": "BTCUSDT",
        "signal_value": 0.82,
        "direction": "long",
        "confidence": "high"
    }
}
```

## Client Examples

### JavaScript/Browser

```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/events');

ws.onopen = () => {
    console.log('Connected to event stream');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`Event: ${data.type}`, data.payload);
    
    switch (data.type) {
        case 'job.completed':
            handleJobComplete(data.payload);
            break;
        case 'trade.entered':
            handleTradeEnter(data.payload);
            break;
        case 'trade.exited':
            handleTradeExit(data.payload);
            break;
    }
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('Disconnected from event stream');
    // Implement reconnection logic
};

function handleJobComplete(payload) {
    console.log(`Job ${payload.job_id} completed`);
    console.log(`Win rate: ${(payload.result.win_rate * 100).toFixed(1)}%`);
}
```

### Python

```python
import asyncio
import websockets
import json

async def event_listener():
    uri = "ws://localhost:8000/api/ws/events"
    
    async with websockets.connect(uri) as ws:
        print("Connected to event stream")
        
        async for message in ws:
            event = json.loads(message)
            event_type = event['type']
            payload = event['payload']
            
            print(f"Event: {event_type}")
            
            if event_type == 'job.completed':
                print(f"  Job {payload['job_id']} completed")
                print(f"  Win rate: {payload['result']['win_rate']:.1%}")
            
            elif event_type == 'trade.entered':
                print(f"  Entered {payload['side']} {payload['symbol']}")
                print(f"  Entry: {payload['entry_price']}")
            
            elif event_type == 'trade.exited':
                print(f"  Exited {payload['symbol']}")
                print(f"  PnL: {payload['pnl_pct']:.2%}")

asyncio.run(event_listener())
```

### Python with Reconnection

```python
import asyncio
import websockets
import json
from typing import Callable

class EventClient:
    def __init__(self, url: str, handlers: dict[str, Callable] = None):
        self.url = url
        self.handlers = handlers or {}
        self.ws = None
        self.running = False
    
    async def connect(self):
        self.running = True
        while self.running:
            try:
                async with websockets.connect(self.url) as ws:
                    self.ws = ws
                    print("Connected")
                    await self._listen()
            except websockets.ConnectionClosed:
                print("Connection closed, reconnecting...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Error: {e}, reconnecting...")
                await asyncio.sleep(5)
    
    async def _listen(self):
        async for message in self.ws:
            event = json.loads(message)
            handler = self.handlers.get(event['type'])
            if handler:
                await handler(event['payload'])
    
    async def stop(self):
        self.running = False
        if self.ws:
            await self.ws.close()

# Usage
async def on_trade_entered(payload):
    print(f"Trade entered: {payload}")

client = EventClient(
    "ws://localhost:8000/api/ws/events",
    handlers={
        'trade.entered': on_trade_entered,
    }
)

asyncio.run(client.connect())
```

## Heartbeat

The server sends periodic ping frames to keep the connection alive. Most WebSocket clients handle this automatically.

If implementing a custom client, respond to ping frames with pong frames.

## Error Handling

### Connection Errors

If the WebSocket connection fails:

1. Wait 5 seconds
2. Attempt to reconnect
3. Use exponential backoff for repeated failures

### Message Errors

Invalid messages are logged server-side. The connection remains open.

## Best Practices

1. **Always handle reconnection** - Connections can drop
2. **Process events asynchronously** - Don't block the message loop
3. **Filter events** - Only process events you care about
4. **Implement heartbeat monitoring** - Detect stale connections
