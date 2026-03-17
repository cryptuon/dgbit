from typing import List
import pandas as pd
from datetime import datetime
from dgbit_core.trading.strategy import TradingStrategy
from dgbit_core.trading.position import Position
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

class Backtester:
    def __init__(self, 
                 initial_capital: float = 10000,
                 transaction_fee: float = 0.001):  # 0.1%
        self.initial_capital = initial_capital
        self.transaction_fee = transaction_fee
        self.strategy = TradingStrategy()
        self.positions: List[Position] = []
        self.capital = initial_capital
        
    def run(self, data: pd.DataFrame) -> pd.DataFrame:
        """Run backtest on historical data"""
        # Train on first 70% of data
        train_size = int(len(data) * 0.7)
        train_data = data.iloc[:train_size]
        test_data = data.iloc[train_size:]
        
        self.strategy.train(train_data)
        
        current_position = None
        results = []
        
        # Simulate trading on test data
        for i in range(len(test_data) - 1):
            current_data = test_data.iloc[:i+1]
            current_candle = current_data.iloc[-1]
            current_time = pd.to_datetime(current_candle['timestamp'])
            
            # Check if we should exit existing position
            if current_position and current_position.is_open:
                # Check if price hit take profit or stop loss during the candle
                if (current_candle['high'] >= current_position.take_profit_price or 
                    current_candle['low'] <= current_position.stop_loss_price):
                    
                    # Use stop loss or take profit price as exit price
                    if current_candle['low'] <= current_position.stop_loss_price:
                        exit_price = current_position.stop_loss_price
                        exit_type = 'stop_loss'
                    else:
                        exit_price = current_position.take_profit_price
                        exit_type = 'take_profit'
                    
                    current_position.exit_price = exit_price
                    current_position.exit_time = current_time
                    
                    # Calculate returns after fees
                    total_fee = self.transaction_fee * 2  # entry and exit
                    net_return = current_position.return_pct() - total_fee
                    self.capital *= (1 + net_return)
                    
                    results.append({
                        'timestamp': current_time,
                        'action': 'exit',
                        'exit_type': exit_type,
                        'price': exit_price,
                        'capital': self.capital,
                        'return': net_return,
                        'position_duration': current_position.duration
                    })
                    
                    current_position = None
            
            # Check if we should enter new position
            if not current_position:
                should_enter, predicted_return = self.strategy.should_enter_trade(current_data)
                
                if should_enter:
                    entry_price = current_data.iloc[-1]['close']
                    tp_price, sl_price = self.strategy.calculate_exit_prices(entry_price)
                    position_size = self.capital  # Using full capital for simplicity
                    
                    current_position = Position(
                        symbol=test_data.iloc[0]['symbol'] if 'symbol' in test_data else 'UNKNOWN',
                        entry_price=entry_price,
                        entry_time=current_time,
                        take_profit_price=tp_price,
                        stop_loss_price=sl_price,
                        position_size=position_size
                    )
                    
                    self.positions.append(current_position)
                    
                    results.append({
                        'timestamp': current_time,
                        'action': 'entry',
                        'price': entry_price,
                        'capital': self.capital,
                        'predicted_return': predicted_return,
                        'take_profit': tp_price,
                        'stop_loss': sl_price
                    })
        
        # Convert results to DataFrame with all required columns
        results_df = pd.DataFrame(results)
        if len(results_df) == 0:
            # Create empty DataFrame with required columns if no trades
            results_df = pd.DataFrame(columns=[
                'timestamp', 'action', 'price', 'capital', 
                'predicted_return', 'return', 'position_duration',
                'take_profit', 'stop_loss', 'exit_type'
            ])
        
        return results_df
    
    def get_performance_metrics(self) -> dict:
        """Calculate performance metrics from backtest"""
        if not self.positions:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'avg_duration': 0.0,
                'final_capital': self.capital,
                'total_return': (self.capital - self.initial_capital) / self.initial_capital
            }
        
        closed_positions = [p for p in self.positions if not p.is_open]
        
        # If no closed positions, return default metrics
        if not closed_positions:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'avg_duration': 0.0,
                'final_capital': self.capital,
                'total_return': (self.capital - self.initial_capital) / self.initial_capital
            }
        
        returns = [p.return_pct() for p in closed_positions]
        durations = [p.duration for p in closed_positions]
        
        return {
            'total_trades': len(closed_positions),
            'win_rate': sum(1 for r in returns if r > 0) / len(returns),
            'avg_return': sum(returns) / len(returns),
            'avg_duration': sum(durations) / len(durations),
            'final_capital': self.capital,
            'total_return': (self.capital - self.initial_capital) / self.initial_capital
        } 
    
    def plot_results(self, data: pd.DataFrame, results: pd.DataFrame, output_dir: str = "reports"):
        """Generate interactive plots of backtest results"""
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create figure with secondary y-axis
        fig = make_subplots(rows=2, cols=1, 
                           shared_xaxes=True,
                           vertical_spacing=0.03,
                           subplot_titles=('Price Action', 'Account Balance'),
                           row_heights=[0.7, 0.3])

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
        entries = results[results['action'] == 'entry']
        fig.add_trace(
            go.Scatter(
                x=entries['timestamp'],
                y=entries['price'],
                mode='markers',
                marker=dict(
                    symbol='triangle-up',
                    size=10,
                    color='green',
                ),
                name='Entry Points'
            ),
            row=1, col=1
        )

        # Add exit points
        exits = results[results['action'] == 'exit']
        fig.add_trace(
            go.Scatter(
                x=exits['timestamp'],
                y=exits['price'],
                mode='markers',
                marker=dict(
                    symbol='triangle-down',
                    size=10,
                    color='red',
                ),
                name='Exit Points'
            ),
            row=1, col=1
        )

        # Add account balance
        fig.add_trace(
            go.Scatter(
                x=results['timestamp'],
                y=results['capital'],
                mode='lines',
                name='Account Balance',
                line=dict(color='blue')
            ),
            row=2, col=1
        )

        # Update layout
        fig.update_layout(
            title='Backtest Results',
            yaxis_title='Price',
            yaxis2_title='Account Balance',
            xaxis_rangeslider_visible=False,
            height=800
        )

        # Save the plot
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{output_dir}/backtest_results_{timestamp}.html"
        fig.write_html(filename)
        
        # Create performance metrics plot
        metrics_fig = go.Figure()
        
        # Add performance metrics
        metrics = self.get_performance_metrics()
        metrics_data = [
            {'metric': 'Win Rate', 'value': f"{metrics['win_rate']*100:.1f}%"},
            {'metric': 'Avg Return', 'value': f"{metrics['avg_return']*100:.2f}%"},
            {'metric': 'Total Return', 'value': f"{metrics['total_return']*100:.2f}%"},
            {'metric': 'Total Trades', 'value': str(metrics['total_trades'])}
        ]
        
        metrics_fig.add_trace(go.Table(
            header=dict(values=['Metric', 'Value'],
                       fill_color='paleturquoise',
                       align='left'),
            cells=dict(values=[[d['metric'] for d in metrics_data],
                              [d['value'] for d in metrics_data]],
                      fill_color='lavender',
                      align='left')
        ))
        
        metrics_fig.update_layout(
            title='Performance Metrics',
            height=400
        )
        
        # Save metrics
        metrics_filename = f"{output_dir}/performance_metrics_{timestamp}.html"
        metrics_fig.write_html(metrics_filename)
