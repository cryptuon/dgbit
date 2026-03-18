"""
dgbit CLI - Unified Command Line Interface

A comprehensive CLI for managing the dgbit trading platform.

Usage:
    dgbit <command> [options] [arguments]

Commands:
    service      Manage services (start, stop, status)
    data         Fetch market data from exchanges
    strategy     Strategy management and backtesting
    trade        Trading operations (orders, positions)
    job          Job management
    backtest     Run backtests
    dashboard    Start web dashboard
    init         Initialize configuration

Examples:
    dgbit service start all
    dgbit data klines BTCUSDT --exchange bybit --interval 1h
    dgbit strategy list
    dgbit backtest --symbol BTCUSDT --strategy wavelet_reversal
    dgbit trade order buy BTCUSDT 0.001 --price 50000
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
from loguru import logger

# Add src to path
SRC_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SRC_DIR))


# =============================================================================
# CLI Groups
# =============================================================================

@click.group()
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Set log level"
)
@click.pass_context
def cli(ctx, verbose, log_level):
    """dgbit - Cryptocurrency Trading Platform CLI"""
    # Setup logging
    level = "DEBUG" if verbose else log_level
    logger.remove()
    logger.add(sys.stdout, level=level, format="{time} | {level} | {message}")

    # Store context
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["log_level"] = level


# =============================================================================
# Service Commands
# =============================================================================

@cli.group(name="service")
def service_cmd():
    """Manage dgbit services"""
    pass


@service_cmd.command(name="start")
@click.argument("service", type=click.Choice(["all", "event_bus", "data", "job", "strategy", "execution"], case_sensitive=False))
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground")
@click.pass_context
def service_start(ctx, service, foreground):
    """Start a service or all services"""
    verbose = ctx.obj.get("verbose", False)

    if service == "all":
        click.echo("Starting all services...")
        from dgbit_services.orchestrator import ServiceBusOrchestrator
        orchestrator = ServiceBusOrchestrator()
        if foreground:
            asyncio.run(orchestrator.run())
        else:
            click.echo("Run 'dgbit-service-bus' in a separate terminal to start all services")
    else:
        # Map service name to command
        cmd_map = {
            "event_bus": ("dgbit_services.events", "run_event_bus_service"),
            "data": ("dgbit_data.service", "run_service"),
            "job": ("dgbit_services.jobs", "run_job_queue_service"),
            "strategy": ("dgbit_services.strategy", "run_strategy_service"),
            "execution": ("dgbit_services.execution", "run_execution_service"),
        }

        module_name, func_name = cmd_map[service]
        import importlib
        module = importlib.import_module(module_name)
        func = getattr(module, func_name)

        click.echo(f"Starting {service} service...")

        if foreground:
            asyncio.run(func())
        else:
            # Start in background
            import subprocess
            cmd = f"python -c 'from {module_name} import {func_name}; asyncio.run({func_name}())'"
            subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            click.echo(f"{service} service started in background")


@service_cmd.command(name="stop")
@click.argument("service", type=click.Choice(["all", "event_bus", "data", "job", "strategy", "execution"], case_sensitive=False))
@click.pass_context
def service_stop(ctx, service):
    """Stop a service or all services"""
    click.echo(f"Stopping {service} service...")


@service_cmd.command(name="status")
@click.pass_context
def service_status(ctx):
    """Show service status"""
    click.echo("Service Status:")
    click.echo("-" * 40)

    # Check each service
    services = ["event_bus", "data", "job", "strategy", "execution"]
    for svc in services:
        click.echo(f"  {svc}: Checking...")


@service_cmd.command(name="logs")
@click.argument("service", type=click.Choice(["all", "event_bus", "data", "job", "strategy", "execution"], case_sensitive=False))
@click.option("--lines", "-n", default=50, help="Number of lines to show")
@click.pass_context
def service_logs(ctx, service, lines):
    """Show service logs"""
    click.echo(f"Showing last {lines} lines of {service} logs...")


# =============================================================================
# Data Commands
# =============================================================================

@cli.group(name="data")
def data_cmd():
    """Fetch market data from exchanges"""
    pass


@data_cmd.command(name="klines")
@click.argument("symbol", type=str)
@click.option("--exchange", "-e", type=click.Choice(["bybit", "binance", "coinbase", "okx"]), default="bybit")
@click.option("--interval", "-i", type=click.Choice(["1m", "5m", "15m", "30m", "1h", "4h", "1d"]), default="1h")
@click.option("--limit", "-l", type=int, default=100)
@click.option("--output", "-o", type=click.Path(), help="Save to file")
@click.pass_context
def data_klines(ctx, symbol, exchange, interval, limit, output):
    """Fetch kline/candlestick data"""
    from dgbit_data.adapters import AdapterFactory, Exchange, Interval

    click.echo(f"Fetching {interval} klines for {symbol} from {exchange}...")

    try:
        adapter = AdapterFactory.create_data_adapter(
            exchange=Exchange(exchange),
            config=ExchangeConfig(testnet=True)
        )

        interval_map = {
            "1m": Interval.M1, "5m": Interval.M5, "15m": Interval.M15,
            "30m": Interval.M30, "1h": Interval.H1, "4h": Interval.H4, "1d": Interval.D1
        }

        klines = adapter.get_klines(
            symbol=symbol,
            interval=interval_map[interval],
            limit=limit
        )

        click.echo(f"Fetched {klines.count} candles")
        click.echo(f"  Start: {klines.start_time}")
        click.echo(f"  End: {klines.end_time}")

        if output:
            with open(output, "w") as f:
                json.dump(klines.to_dict(), f, indent=2, default=str)
            click.echo(f"Saved to {output}")
        else:
            # Show last 5 candles
            click.echo("\nLatest candles:")
            for k in klines.data[-5:]:
                click.echo(f"  {k.timestamp.strftime('%Y-%m-%d %H:%M')} | O: {k.open:.2f} H: {k.high:.2f} L: {k.low:.2f} C: {k.close:.2f} V: {k.volume:.2f}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@data_cmd.command(name="tickers")
@click.option("--exchange", "-e", type=click.Choice(["bybit", "binance", "coinbase", "okx"]), default="bybit")
@click.option("--symbol", "-s", help="Specific symbol")
@click.pass_context
def data_tickers(ctx, exchange, symbol):
    """Fetch market tickers"""
    from dgbit_data.adapters import AdapterFactory, Exchange

    click.echo(f"Fetching tickers from {exchange}...")

    try:
        adapter = AdapterFactory.create_data_adapter(
            exchange=Exchange(exchange),
            config=ExchangeConfig(testnet=True)
        )

        tickers = adapter.get_tickers(symbol=symbol)

        click.echo(f"Found {len(tickers)} tickers")
        for t in tickers[:10]:
            click.echo(f"  {t.symbol}: ${t.price:,.2f} (24h: {t.change_24h:+.2f}%)")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@data_cmd.command(name="symbols")
@click.option("--exchange", "-e", type=click.Choice(["bybit", "binance", "coinbase", "okx"]), default="bybit")
@click.pass_context
def data_symbols(ctx, exchange):
    """List available trading pairs"""
    from dgbit_data.adapters import AdapterFactory, Exchange

    click.echo(f"Fetching symbols from {exchange}...")

    try:
        adapter = AdapterFactory.create_data_adapter(
            exchange=Exchange(exchange),
            config=ExchangeConfig(testnet=True)
        )

        symbols = adapter.get_symbols()

        click.echo(f"Found {len(symbols)} symbols:")
        for s in symbols[:20]:
            click.echo(f"  {s.symbol}: {s.base}/{s.quote}")
        if len(symbols) > 20:
            click.echo(f"  ... and {len(symbols) - 20} more")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


# =============================================================================
# Strategy Commands
# =============================================================================

@cli.group(name="strategy")
def strategy_cmd():
    """Strategy management"""
    pass


@strategy_cmd.command(name="list")
@click.pass_context
def strategy_list(ctx):
    """List available strategies"""
    from dgbit_core.trading.strategy import StrategyRegistry

    registry = StrategyRegistry()
    strategies = registry.list_strategies()

    click.echo("Available Strategies:")
    click.echo("-" * 60)
    for name, metadata in strategies.items():
        click.echo(f"  {name} (v{metadata.version})")


@strategy_cmd.command(name="info")
@click.argument("name", type=str)
@click.pass_context
def strategy_info(ctx, name):
    """Show strategy information"""
    from dgbit_core.trading.strategy import StrategyRegistry

    try:
        registry = StrategyRegistry()
        strategy_class = registry.get(name)
        if strategy_class:
            metadata = strategy_class.metadata
            click.echo(f"Strategy: {metadata.name}")
            click.echo(f"  Version: {metadata.version}")
            click.echo(f"  Description: {metadata.description}")
            click.echo(f"  Parameters:")
            for param, info in metadata.parameters_schema.items():
                click.echo(f"    {param}: {info}")
        else:
            click.echo(f"Unknown strategy: {name}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@strategy_cmd.command(name="signal")
@click.argument("strategy_name", type=str)
@click.argument("symbol", type=str)
@click.option("--data", "-d", type=click.Path(exists=True), help="CSV data file")
@click.pass_context
def strategy_signal(ctx, strategy_name, symbol, data):
    """Generate a trading signal"""
    from dgbit_core.trading.strategy import StrategyRegistry
    import pandas as pd

    click.echo(f"Generating signal for {strategy_name} on {symbol}...")

    try:
        registry = StrategyRegistry()
        strategy = registry.create(strategy_name, {})

        if data:
            df = pd.read_csv(data)
        else:
            # Fetch from exchange
            from dgbit_data.adapters import AdapterFactory, Exchange, Interval
            adapter = AdapterFactory.create_data_adapter(
                exchange=Exchange.BINANCE,
                config=ExchangeConfig(testnet=True)
            )
            klines = adapter.get_klines(
                symbol=symbol,
                interval=Interval.H1,
                limit=200
            )
            df = pd.DataFrame([{
                "timestamp": k.timestamp,
                "open": k.open,
                "high": k.high,
                "low": k.low,
                "close": k.close,
                "volume": k.volume,
            } for k in klines.data])

        signal_value = strategy.generate_signal(df)

        click.echo(f"Signal value: {signal_value:.4f}")

        should_enter, confidence, direction = strategy.should_enter(df)
        click.echo(f"Should enter: {should_enter}")
        click.echo(f"Confidence: {confidence:.2f}")
        click.echo(f"Direction: {direction.value}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


# =============================================================================
# Backtest Commands
# =============================================================================

@cli.group(name="backtest")
def backtest_cmd():
    """Backtesting commands"""
    pass


@backtest_cmd.command(name="run")
@click.option("--symbol", "-s", default="BTCUSDT", help="Trading pair")
@click.option("--interval", "-i", default="1h", type=click.Choice(["1m", "5m", "15m", "30m", "1h", "4h", "1d"]))
@click.option("--strategy", "-t", default="wavelet_reversal", help="Strategy to use")
@click.option("--initial-capital", "-c", default=10000.0, type=float)
@click.option("--limit", "-l", default=1000, type=int)
@click.option("--output", "-o", type=click.Path(), help="Save results JSON")
@click.pass_context
def backtest_run(ctx, symbol, interval, strategy, initial_capital, limit, output):
    """Run a backtest"""
    from dgbit_backtest import Backtester, BacktestConfig
    from dgbit_data.adapters import AdapterFactory, Exchange, Interval
    import pandas as pd

    click.echo(f"Running backtest...")
    click.echo(f"  Symbol: {symbol}")
    click.echo(f"  Interval: {interval}")
    click.echo(f"  Strategy: {strategy}")
    click.echo(f"  Initial Capital: ${initial_capital:,.2f}")

    try:
        # Fetch data
        click.echo("\nFetching data...")
        adapter = AdapterFactory.create_data_adapter(
            exchange=Exchange.BINANCE,
            config=ExchangeConfig(testnet=True)
        )

        interval_map = {
            "1m": Interval.M1, "5m": Interval.M5, "15m": Interval.M15,
            "30m": Interval.M30, "1h": Interval.H1, "4h": Interval.H4, "1d": Interval.D1
        }

        klines = adapter.get_klines(
            symbol=symbol,
            interval=interval_map[interval],
            limit=limit
        )

        df = pd.DataFrame([{
            "timestamp": k.timestamp,
            "open": k.open,
            "high": k.high,
            "low": k.low,
            "close": k.close,
            "volume": k.volume,
        } for k in klines.data])

        click.echo(f"  Data points: {len(df)}")

        # Run backtest
        click.echo("\nRunning backtest...")
        config = BacktestConfig(
            initial_capital=initial_capital,
            transaction_fee=0.001,
        )

        backtester = Backtester(config=config)
        results = backtester.run(df, strategy_name=strategy)

        # Show results
        click.echo("\n" + "=" * 60)
        click.echo("Backtest Results:")
        click.echo("=" * 60)
        click.echo(f"  Final Capital: ${results.final_capital:,.2f}")
        click.echo(f"  Total Return: {results.total_return_pct:.2f}%")
        click.echo(f"  Win Rate: {results.win_rate:.2f}%")
        click.echo(f"  Total Trades: {results.total_trades}")
        click.echo(f"  Max Drawdown: {results.max_drawdown:.2f}%")
        click.echo(f"  Sharpe Ratio: {results.sharpe_ratio:.2f}")

        if output:
            with open(output, "w") as f:
                json.dump(results.to_dict(), f, indent=2, default=str)
            click.echo(f"\nResults saved to {output}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


# =============================================================================
# Trading Commands
# =============================================================================

@cli.group(name="trade")
def trade_cmd():
    """Trading operations"""
    pass


@trade_cmd.command(name="order")
@click.argument("side", type=click.Choice(["buy", "sell"]))
@click.argument("symbol", type=str)
@click.argument("quantity", type=float)
@click.option("--price", "-p", type=float, help="Limit price")
@click.option("--exchange", "-e", type=click.Choice(["bybit", "binance", "coinbase", "okx"]), default="bybit")
@click.option("--type", "-t", type=click.Choice(["market", "limit", "stop"]), default="market")
@click.pass_context
def trade_order(ctx, side, symbol, quantity, price, exchange, order_type):
    """Create an order"""
    from dgbit_data.adapters import AdapterFactory, Exchange, ExchangeConfig
    from dgbit_data.adapters.base import Side as OrderSide, OrderType as OType

    click.echo(f"Creating {order_type} {side} order...")
    click.echo(f"  Symbol: {symbol}")
    click.echo(f"  Quantity: {quantity}")
    if price:
        click.echo(f"  Price: ${price:,.2f}")

    try:
        adapter = AdapterFactory.create_execution_adapter(
            exchange=Exchange(exchange),
            config=ExchangeConfig(testnet=True)
        )

        order = adapter.create_order(
            symbol=symbol,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            order_type=OType.MARKET if order_type == "market" else OType.LIMIT,
            quantity=quantity,
            price=price,
        )

        click.echo(f"\nOrder created:")
        click.echo(f"  Order ID: {order.order_id}")
        click.echo(f"  Status: {order.status.value}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@trade_cmd.command(name="positions")
@click.option("--exchange", "-e", type=click.Choice(["bybit", "binance", "okx"]), default="bybit")
@click.pass_context
def trade_positions(ctx, exchange):
    """Show open positions"""
    from dgbit_data.adapters import AdapterFactory, Exchange, ExchangeConfig

    click.echo(f"Fetching positions from {exchange}...")

    try:
        adapter = AdapterFactory.create_execution_adapter(
            exchange=Exchange(exchange),
            config=ExchangeConfig(testnet=True)
        )

        positions = adapter.get_positions()

        if positions:
            click.echo(f"\nOpen Positions:")
            click.echo("-" * 60)
            for pos in positions:
                click.echo(f"  {pos.symbol} ({pos.side.value}):")
                click.echo(f"    Size: {pos.quantity}")
                click.echo(f"    Entry: ${pos.entry_price:,.2f}")
                click.echo(f"    Mark: ${pos.mark_price:,.2f}")
                click.echo(f"    P&L: ${pos.unrealized_pnl:,.2f}")
        else:
            click.echo("No open positions")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@trade_cmd.command(name="balance")
@click.option("--exchange", "-e", type=click.Choice(["bybit", "binance", "coinbase", "okx"]), default="bybit")
@click.pass_context
def trade_balance(ctx, exchange):
    """Show account balance"""
    from dgbit_data.adapters import AdapterFactory, Exchange, ExchangeConfig

    click.echo(f"Fetching balance from {exchange}...")

    try:
        adapter = AdapterFactory.create_execution_adapter(
            exchange=Exchange(exchange),
            config=ExchangeConfig(testnet=True)
        )

        balance = adapter.get_balance()

        click.echo("\nAccount Balance:")
        click.echo("-" * 40)
        for asset, amount in balance.items():
            click.echo(f"  {asset}: {amount:.8f}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


# =============================================================================
# Job Commands
# =============================================================================

@cli.group(name="job")
def job_cmd():
    """Job management"""
    pass


@job_cmd.command(name="list")
@click.option("--status", type=click.Choice(["pending", "running", "completed", "failed"]))
@click.option("--limit", "-l", default=50, type=int)
@click.pass_context
def job_list(ctx, status, limit):
    """List jobs"""
    click.echo("Fetching jobs...")

    try:
        from dgbit_api.services.job_service import JobService
        from dgbit_api.db.models import JobStatus

        status_enum = JobStatus(status) if status else None
        jobs = asyncio.run(JobService.list_jobs(status=status_enum, limit=limit))

        click.echo(f"\nJobs:")
        click.echo("-" * 80)
        for job in jobs:
            click.echo(f"  {job.uuid} | {job.job_type} | {job.status} | {job.created_at}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@job_cmd.command(name="status")
@click.argument("job_id", type=str)
@click.pass_context
def job_status(ctx, job_id):
    """Get job status"""
    click.echo(f"Fetching job {job_id}...")

    try:
        from dgbit_api.services.job_service import JobService

        job = asyncio.run(JobService.get_by_uuid(job_id))

        if job:
            click.echo(f"\nJob: {job.uuid}")
            click.echo(f"  Type: {job.job_type}")
            click.echo(f"  Status: {job.status}")
            click.echo(f"  Created: {job.created_at}")
            if job.started_at:
                click.echo(f"  Started: {job.started_at}")
            if job.completed_at:
                click.echo(f"  Completed: {job.completed_at}")
        else:
            click.echo(f"Job not found: {job_id}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


# =============================================================================
# Utility Commands
# =============================================================================

@cli.group(name="util")
def util_cmd():
    """Utility commands"""
    pass


@util_cmd.command(name="health")
@click.pass_context
def util_health(ctx):
    """Check health of all components"""
    click.echo("Health Check:")
    click.echo("-" * 40)

    # Check services
    click.echo("\nExchange Adapters:")
    from dgbit_data.adapters import AdapterFactory

    exchanges = AdapterFactory.health_check_all(ExchangeConfig(testnet=True))
    for exchange, healthy in exchanges.items():
        status = "✓" if healthy else "✗"
        click.echo(f"  [{status}] {exchange}")


@util_cmd.command(name="version")
@click.pass_context
def util_version(ctx):
    """Show version information"""
    from importlib.metadata import version, PackageNotFoundError

    click.echo("dgbit Platform Version Info")
    click.echo("-" * 40)

    packages = [
        "dgbit-api",
        "dgbit-core",
        "dgbit-data",
        "dgbit-services",
    ]

    for pkg in packages:
        try:
            v = version(pkg)
            click.echo(f"  {pkg}: {v}")
        except PackageNotFoundError:
            click.echo(f"  {pkg}: Not installed")


# =============================================================================
# Dashboard Command
# =============================================================================

@cli.command(name="dashboard")
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind")
@click.pass_context
def dashboard_cmd(ctx, host, port):
    """Start the web dashboard"""
    click.echo(f"Starting dashboard at http://{host}:{port}")
    click.echo("Press Ctrl+C to stop")

    import uvicorn
    from dgbit_api.main import app

    uvicorn.run(app, host=host, port=port, reload=False)


# =============================================================================
# Initialize Command
# =============================================================================

@cli.command(name="init")
@click.option("--force", "-f", is_flag=True, help="Force re-initialization")
@click.pass_context
def init_cmd(ctx, force):
    """Initialize dgbit configuration"""
    click.echo("Initializing dgbit...")

    # Create config directory
    config_dir = Path.home() / ".dgbit"
    config_dir.mkdir(exist_ok=True)

    # Create default config
    config_file = config_dir / "config.yaml"

    if config_file.exists() and not force:
        click.echo(f"Config already exists at {config_file}")
        return

    default_config = """
# dgbit Configuration
# Generated by dgbit init

# API Settings
api:
  host: "0.0.0.0"
  port: 8000
  debug: false

# Database
database:
  url: "sqlite://data/dgbit.db"

# Exchanges
exchanges:
  bybit:
    enabled: true
    testnet: true
    api_key: ""
    api_secret: ""
  binance:
    enabled: true
    testnet: true
    api_key: ""
    api_secret: ""

# Logging
logging:
  level: "INFO"
  format: "json"
"""

    with open(config_file, "w") as f:
        f.write(default_config)

    click.echo(f"Config created at {config_file}")
    click.echo("\nEdit the config file to add your API keys.")


@cli.command(name="frontend")
@click.option("--port", "-p", default=3000, help="Port to run on")
@click.pass_context
def frontend_cmd(ctx, port):
    """Start the frontend development server"""
    click.echo(f"Starting frontend at http://localhost:{port}")
    click.echo("Press Ctrl+C to stop")

    import subprocess
    import os

    # Look for dgbit-ui in sibling directory
    current_dir = Path(__file__).parent.parent.parent
    frontend_dir = current_dir.parent / "dgbit-ui"

    if not frontend_dir.exists():
        click.echo(f"Error: dgbit-ui not found at {frontend_dir}")
        return

    env = os.environ.copy()
    env['PORT'] = str(port)

    subprocess.run(['npm', 'run', 'dev'], cwd=str(frontend_dir), env=env, check=True)


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for the CLI."""
    cli(obj={})


def run_frontend():
    """Run the frontend development server."""
    import subprocess
    import os

    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
    subprocess.run(['npm', 'run', 'dev'], cwd=frontend_dir, check=True)


if __name__ == "__main__":
    main()
