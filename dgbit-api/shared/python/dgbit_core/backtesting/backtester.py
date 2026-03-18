from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

from dgbit_core.trading.strategy import BaseStrategy, WaveletReversalStrategy
from dgbit_core.trading.position import Position, PositionSide


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    initial_capital: float = 10000.0
    transaction_fee: float = 0.001  # 0.1%
    train_split: float = 0.7  # 70% train, 30% test
    report_dir: str = "reports"


@dataclass
class Trade:
    """Represents a single trade in the backtest."""
    timestamp: datetime
    action: str  # 'entry' or 'exit'
    symbol: str
    price: float
    quantity: float
    capital: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    duration_minutes: Optional[float] = None
    exit_type: Optional[str] = None  # 'take_profit' or 'stop_loss'


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    trades: List[Trade]
    equity_curve: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    config: BacktestConfig


class Backtester:
    """Backtesting engine with clean separation of concerns."""

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.strategy: BaseStrategy = WaveletReversalStrategy()
        self.positions: List[Position] = []
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = []
        self.capital = self.config.initial_capital

    def run(self, data: pd.DataFrame) -> BacktestResult:
        """Run backtest on historical data."""
        # Validate data
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"Missing required column: {col}")

        # Reset state
        self.capital = self.config.initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = []

        # Split data
        train_size = int(len(data) * self.config.train_split)
        train_data = data.iloc[:train_size]
        test_data = data.iloc[train_size:]

        # Train strategy
        self.strategy.train(train_data)

        # Run simulation
        self._simulate(test_data)

        # Calculate metrics
        metrics = self._calculate_metrics()

        return BacktestResult(
            trades=self.trades,
            equity_curve=self.equity_curve,
            metrics=metrics,
            config=self.config,
        )

    def _simulate(self, data: pd.DataFrame) -> None:
        """Simulate trading on test data."""
        current_position: Optional[Position] = None

        for i in range(len(data) - 1):
            current_data = data.iloc[:i + 1]
            current_candle = current_data.iloc[-1]
            current_time = pd.to_datetime(current_candle['timestamp'])
            symbol = data.iloc[0]['symbol'] if 'symbol' in data.columns else 'UNKNOWN'

            # Record equity
            self.equity_curve.append({
                'timestamp': current_time,
                'capital': self.capital,
            })

            # Check exit conditions
            if current_position and current_position.is_open:
                exit_result = self._check_exit(current_position, current_candle, current_time)
                if exit_result:
                    self._close_position(current_position, exit_result, current_time)
                    current_position = None

            # Check entry conditions
            if not current_position:
                result = self.strategy.should_enter(current_data)
                # Handle both old (2-tuple) and new (3-tuple) interfaces
                if len(result) == 2:
                    should_enter, signal_value = result
                    direction = PositionSide.LONG
                else:
                    should_enter, signal_value, direction = result
                    # Convert TradeDirection enum to PositionSide
                    if direction.value == "short":
                        direction = PositionSide.SHORT
                    else:
                        direction = PositionSide.LONG

                if should_enter:
                    current_position = self._open_position(
                        current_candle, current_time, symbol, signal_value, direction
                    )

    def _check_exit(
        self,
        position: Position,
        candle: pd.Series,
        current_time: datetime,
    ) -> Optional[tuple]:
        """Check if position should be exited. Returns (exit_price, exit_type) if yes."""
        if candle['high'] >= position.take_profit_price:
            return position.take_profit_price, 'take_profit'
        elif candle['low'] <= position.stop_loss_price:
            return position.stop_loss_price, 'stop_loss'
        return None

    def _open_position(
        self,
        candle: pd.Series,
        current_time: datetime,
        symbol: str,
        signal_value: float,
        direction: PositionSide = PositionSide.LONG,
    ) -> Position:
        """Open a new position."""
        entry_price = candle['close']
        tp_price, sl_price = self.strategy.calculate_exit_prices(entry_price, direction)
        position_size = self.capital  # Use full capital

        position = Position(
            symbol=symbol,
            side=direction,
            entry_price=entry_price,
            entry_time=current_time,
            quantity=position_size,
            take_profit_price=tp_price,
            stop_loss_price=sl_price,
        )
        self.positions.append(position)

        # Record trade
        trade = Trade(
            timestamp=current_time,
            action='entry',
            symbol=symbol,
            price=entry_price,
            quantity=position_size,
            capital=self.capital,
        )
        self.trades.append(trade)

        return position

    def _close_position(
        self,
        position: Position,
        exit_info: tuple,
        current_time: datetime,
    ) -> None:
        """Close a position and record the trade."""
        exit_price, exit_type = exit_info

        # Calculate returns
        total_fee = self.config.transaction_fee * 2  # entry and exit
        raw_return = position.return_pct()
        net_return = raw_return - total_fee
        self.capital *= (1 + net_return)

        # Calculate duration
        duration = (current_time - position.entry_time).total_seconds() / 60

        # Record trade
        trade = Trade(
            timestamp=current_time,
            action='exit',
            symbol=position.symbol,
            price=exit_price,
            quantity=position.quantity,
            capital=self.capital,
            pnl=(self.capital - position.quantity),
            pnl_pct=net_return * 100,
            duration_minutes=duration,
            exit_type=exit_type,
        )
        self.trades.append(trade)

        # Close position
        position.close(exit_price, current_time)

    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics."""
        closed_positions = [p for p in self.positions if not p.is_open]

        if not closed_positions:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'avg_duration': 0.0,
                'final_capital': self.capital,
                'total_return': (self.capital - self.config.initial_capital) / self.config.initial_capital,
                'max_drawdown': 0.0,
                'profit_factor': 0.0,
            }

        # Calculate returns and durations
        returns = [p.return_pct() for p in closed_positions]
        durations = [p.duration for p in closed_positions]

        # Win rate
        wins = sum(1 for r in returns if r > 0)
        win_rate = wins / len(returns) if returns else 0.0

        # Profit factor
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Max drawdown
        equity = [e['capital'] for e in self.equity_curve]
        max_equity = max(equity)
        drawdowns = [(max_equity - e) / max_equity for e in equity]
        max_drawdown = max(drawdowns) if drawdowns else 0.0

        return {
            'total_trades': len(closed_positions),
            'win_rate': win_rate,
            'avg_return': sum(returns) / len(returns),
            'avg_duration': sum(durations) / len(durations),
            'final_capital': self.capital,
            'total_return': (self.capital - self.config.initial_capital) / self.config.initial_capital,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'wins': wins,
            'losses': len(closed_positions) - wins,
        }

    def plot_results(self, data: pd.DataFrame, result: BacktestResult, output_dir: str = None) -> Dict[str, str]:
        """Generate interactive plots of backtest results."""
        output_dir = output_dir or self.config.report_dir
        os.makedirs(output_dir, exist_ok=True)

        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        files = {}

        # Create figure with secondary y-axis
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=('Price Action', 'Account Balance'),
            row_heights=[0.7, 0.3]
        )

        # Add candlestick
        fig.add_trace(
            go.Candlestick(
                x=data['timestamp'],
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name='Price'
            ),
            row=1, col=1
        )

        # Add entry points
        entries = [t for t in self.trades if t.action == 'entry']
        fig.add_trace(
            go.Scatter(
                x=[t.timestamp for t in entries],
                y=[t.price for t in entries],
                mode='markers',
                marker=dict(symbol='triangle-up', size=10, color='green'),
                name='Entry Points'
            ),
            row=1, col=1
        )

        # Add exit points
        exits = [t for t in self.trades if t.action == 'exit']
        fig.add_trace(
            go.Scatter(
                x=[t.timestamp for t in exits],
                y=[t.price for t in exits],
                mode='markers',
                marker=dict(symbol='triangle-down', size=10, color='red'),
                name='Exit Points'
            ),
            row=1, col=1
        )

        # Add account balance
        fig.add_trace(
            go.Scatter(
                x=[e['timestamp'] for e in self.equity_curve],
                y=[e['capital'] for e in self.equity_curve],
                mode='lines',
                name='Account Balance',
                line=dict(color='blue')
            ),
            row=2, col=1
        )

        fig.update_layout(
            title='Backtest Results',
            yaxis_title='Price',
            yaxis2_title='Account Balance',
            xaxis_rangeslider_visible=False,
            height=800
        )

        # Save plot
        filename = f"{output_dir}/backtest_results_{timestamp}.html"
        fig.write_html(filename)
        files['chart'] = filename

        # Create metrics table
        metrics_fig = go.Figure()
        metrics = result.metrics
        metrics_data = [
            {'metric': 'Win Rate', 'value': f"{metrics['win_rate']*100:.1f}%"},
            {'metric': 'Avg Return', 'value': f"{metrics['avg_return']*100:.2f}%"},
            {'metric': 'Total Return', 'value': f"{metrics['total_return']*100:.2f}%"},
            {'metric': 'Max Drawdown', 'value': f"{metrics['max_drawdown']*100:.2f}%"},
            {'metric': 'Total Trades', 'value': str(metrics['total_trades'])},
            {'metric': 'Profit Factor', 'value': f"{metrics['profit_factor']:.2f}"},
        ]

        metrics_fig.add_trace(go.Table(
            header=dict(values=['Metric', 'Value'], fill_color='paleturquoise', align='left'),
            cells=dict(values=[[d['metric'] for d in metrics_data], [d['value'] for d in metrics_data]],
                      fill_color='lavender', align='left')
        ))

        metrics_fig.update_layout(title='Performance Metrics', height=400)

        metrics_filename = f"{output_dir}/performance_metrics_{timestamp}.html"
        metrics_fig.write_html(metrics_filename)
        files['metrics'] = metrics_filename

        return files
