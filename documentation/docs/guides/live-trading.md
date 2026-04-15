# Live Trading Guide

This guide covers deploying dgbit for live trading on Bybit.

!!! warning "Risk Warning"
    Live trading involves real financial risk. Always start with testnet, use proper risk management, and never risk more than you can afford to lose.

## Prerequisites

Before live trading:

1. **Backtest thoroughly** - Validate strategy performance
2. **Paper trade** - Test on Bybit testnet
3. **Understand the risks** - Markets can move against you
4. **Set up monitoring** - Track positions and alerts

## Setting Up API Keys

### Testnet (Recommended First)

1. Create account at [testnet.bybit.com](https://testnet.bybit.com)
2. Go to Account > API Management
3. Create API key with Trade permission
4. Configure in `.env`:

```env
BYBIT_API_KEY=your_testnet_key
BYBIT_API_SECRET=your_testnet_secret
BYBIT_TESTNET=true
```

### Mainnet (Real Funds)

1. Log in to [bybit.com](https://www.bybit.com)
2. Go to Account > API Management
3. Create API key with:
    - **Read** permission (required)
    - **Trade** permission (required)
    - IP whitelist (recommended)
4. Configure in `.env`:

```env
BYBIT_API_KEY=your_mainnet_key
BYBIT_API_SECRET=your_mainnet_secret
BYBIT_TESTNET=false
```

## Real-Time Trader

### Basic Setup

```python
from dgbit_core.trading.realtime_trader import RealtimeTrader
from dgbit_core.trading.strategy import WaveletReversalStrategy
from dgbit_core.data.data_fetcher import BybitDataFetcher

# Initialize components
fetcher = BybitDataFetcher(
    api_key="your_key",
    api_secret="your_secret",
    testnet=True,  # Start with testnet!
)

strategy = WaveletReversalStrategy(
    min_signal_threshold=0.8,  # Higher threshold for live
    take_profit_pct=0.02,
    stop_loss_pct=0.01,
)

# Create trader
trader = RealtimeTrader(
    fetcher=fetcher,
    strategy=strategy,
    symbol="BTCUSDT",
    position_size_pct=0.1,  # Risk 10% per trade
)
```

### Running the Trader

```python
import asyncio

async def main():
    # Start trading
    await trader.start()
    
    try:
        # Run for specified duration
        await asyncio.sleep(3600)  # 1 hour
    finally:
        await trader.stop()

asyncio.run(main())
```

### Position Management

```python
# Check current positions
positions = await trader.get_positions()
for pos in positions:
    print(f"{pos.symbol}: {pos.side} {pos.quantity} @ {pos.entry_price}")
    print(f"  Unrealized PnL: {pos.unrealized_pnl}")

# Close a position manually
await trader.close_position("BTCUSDT")

# Close all positions
await trader.close_all_positions()
```

## Via the API

### Place Orders

```python
import httpx

# Market buy order
response = httpx.post(
    "http://localhost:8000/api/execution/orders",
    json={
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "market",
        "quantity": 0.001,
    }
)
order = response.json()
print(f"Order placed: {order['order_id']}")
```

### Monitor Positions

```python
# Get open positions
response = httpx.get("http://localhost:8000/api/execution/positions")
positions = response.json()

for pos in positions:
    print(f"{pos['symbol']}: {pos['side']} {pos['quantity']}")
```

### WebSocket Events

Subscribe to real-time updates:

```python
import asyncio
import websockets
import json

async def monitor_trades():
    uri = "ws://localhost:8000/api/ws/events"
    
    async with websockets.connect(uri) as ws:
        while True:
            message = await ws.recv()
            event = json.loads(message)
            
            if event['type'] == 'trade.entered':
                print(f"Entered: {event['payload']}")
            elif event['type'] == 'trade.exited':
                print(f"Exited: {event['payload']}")
            elif event['type'] == 'signal.generated':
                print(f"Signal: {event['payload']}")

asyncio.run(monitor_trades())
```

## Risk Management

### Position Sizing

Never risk more than a small percentage per trade:

```python
# Calculate position size
def calculate_position_size(
    capital: float,
    risk_pct: float,
    stop_loss_pct: float,
    price: float,
) -> float:
    """
    Calculate position size based on risk.
    
    Args:
        capital: Total capital
        risk_pct: Max risk per trade (e.g., 0.01 = 1%)
        stop_loss_pct: Stop loss percentage
        price: Current price
    
    Returns:
        Position size in base currency
    """
    risk_amount = capital * risk_pct
    position_value = risk_amount / stop_loss_pct
    position_size = position_value / price
    return position_size

# Example: $10,000 capital, 1% risk, 2% stop loss
size = calculate_position_size(10000, 0.01, 0.02, 50000)
print(f"Position size: {size:.6f} BTC")  # 0.01 BTC
```

### Maximum Drawdown Limits

Implement circuit breakers:

```python
class RiskManager:
    def __init__(self, max_daily_loss_pct=0.05, max_drawdown_pct=0.10):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.starting_capital = None
        self.peak_capital = None
        self.daily_starting_capital = None
    
    def check_limits(self, current_capital: float) -> bool:
        """Returns True if trading should continue."""
        if self.starting_capital is None:
            self.starting_capital = current_capital
            self.peak_capital = current_capital
            self.daily_starting_capital = current_capital
        
        # Update peak
        self.peak_capital = max(self.peak_capital, current_capital)
        
        # Check daily loss
        daily_loss = (self.daily_starting_capital - current_capital) / self.daily_starting_capital
        if daily_loss > self.max_daily_loss_pct:
            print(f"Daily loss limit hit: {daily_loss:.2%}")
            return False
        
        # Check drawdown
        drawdown = (self.peak_capital - current_capital) / self.peak_capital
        if drawdown > self.max_drawdown_pct:
            print(f"Drawdown limit hit: {drawdown:.2%}")
            return False
        
        return True
```

### Stop Loss Orders

Always use stop losses:

```python
# Place order with stop loss
response = httpx.post(
    "http://localhost:8000/api/execution/orders",
    json={
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "market",
        "quantity": 0.001,
        "stop_loss": 49000,  # Stop loss price
        "take_profit": 52000,  # Take profit price
    }
)
```

## Monitoring

### Logging

Enable detailed logging for live trading:

```env
LOG_LEVEL=DEBUG
```

### Health Checks

Monitor system health:

```bash
# Check API health
curl http://localhost:8000/api/health

# Check worker status
docker-compose ps
```

### Alerts

Set up alerts for critical events:

```python
import smtplib
from email.message import EmailMessage

def send_alert(subject: str, body: str):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = f"[dgbit] {subject}"
    msg['From'] = "alerts@example.com"
    msg['To'] = "you@example.com"
    
    with smtplib.SMTP('smtp.example.com', 587) as server:
        server.send_message(msg)

# Example: Alert on large drawdown
if current_drawdown > 0.05:
    send_alert(
        "Drawdown Alert",
        f"Current drawdown: {current_drawdown:.2%}"
    )
```

## Deployment Checklist

Before going live:

- [ ] Backtested with realistic fees and slippage
- [ ] Tested on Bybit testnet
- [ ] API keys configured securely
- [ ] Risk limits set (position size, max drawdown)
- [ ] Monitoring and alerts configured
- [ ] Emergency stop procedure documented
- [ ] Backup plan if system goes down

## Emergency Procedures

### Close All Positions

```bash
# Via API
curl -X POST http://localhost:8000/api/execution/close-all

# Via Bybit directly
python -c "
from pybit.unified_trading import HTTP
session = HTTP(api_key='...', api_secret='...')
session.cancel_all_orders(category='spot')
"
```

### Stop the System

```bash
# Docker
docker-compose down

# Direct
pkill -f "uvicorn dgbit_api"
pkill -f "backtest_runner"
```

## Next Steps

- [Docker Deployment](../deployment/docker.md) - Production deployment
- [Monitoring](../deployment/monitoring.md) - Set up monitoring
- [Custom Strategies](custom-strategies.md) - Build your own strategies
