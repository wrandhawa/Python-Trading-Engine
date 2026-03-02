import pandas as pd
import numpy as np
from typing import List, Dict, Any

class Strategy:
    """Base class for all backtesting strategies."""
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a DataFrame of market data and returns it with a 'Signal' column.
        1 = Buy, -1 = Sell, 0 = Hold.
        """
        raise NotImplementedError("Strategies must implement generate_signals method")

class RSIMomentumStrategy(Strategy):
    """Buys when RSI <= 30 and sells when RSI >= 70."""
    def __init__(self, period: int = 14, overbought: int = 70, oversold: int = 30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Calculate RSI using pandas-ta if available
        import pandas_ta as ta
        df['RSI'] = ta.rsi(df['Close'], length=self.period)

        # Initialize signals to 0
        df['Signal'] = 0

        # We use a simple boolean mask to map 1 and -1 to the 'Signal' column
        # Buy signal (1) where RSI drops below oversold
        df.loc[df['RSI'] <= self.oversold, 'Signal'] = 1

        # Sell signal (-1) where RSI goes above overbought
        df.loc[df['RSI'] >= self.overbought, 'Signal'] = -1

        return df

class SMACrossoverStrategy(Strategy):
    """Buys when Fast SMA > Slow SMA, Sells when Fast SMA < Slow SMA."""
    def __init__(self, fast_period: int = 10, slow_period: int = 30):
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        import pandas_ta as ta
        df['Fast_SMA'] = ta.sma(df['Close'], length=self.fast_period)
        df['Slow_SMA'] = ta.sma(df['Close'], length=self.slow_period)

        df['Signal'] = 0

        # When Fast SMA crosses above Slow SMA, buy
        df.loc[df['Fast_SMA'] > df['Slow_SMA'], 'Signal'] = 1

        # When Fast SMA crosses below Slow SMA, sell
        df.loc[df['Fast_SMA'] < df['Slow_SMA'], 'Signal'] = -1

        # Smooth out signals (we only trade when the signal changes, not continuously)
        # 1 means Buy, -1 means Sell, so difference will be 2 or -2
        df['Signal'] = df['Signal'].diff()

        # Map back to 1 and -1, ignore holding periods (0)
        df['Signal'] = np.where(df['Signal'] > 0, 1,
                       np.where(df['Signal'] < 0, -1, 0))

        return df

class Backtester:
    """
    Simulates trading a given strategy against historical data.
    """
    def __init__(self, data: pd.DataFrame, strategy: Strategy, initial_capital: float = 10000.0):
        self.data = data.copy()
        self.strategy = strategy
        self.initial_capital = initial_capital

        # Ensure we have required columns
        if 'Close' not in self.data.columns:
            raise ValueError("Data must contain a 'Close' price column.")

    def run(self) -> pd.DataFrame:
        """Runs the backtest and returns a DataFrame with portfolio values over time."""
        # 1. Generate trading signals
        self.data = self.strategy.generate_signals(self.data)

        # Initialize portfolio tracking
        positions = pd.DataFrame(index=self.data.index).fillna(0.0)
        positions['Asset'] = 0.0 # Number of shares held

        portfolio = pd.DataFrame(index=self.data.index)
        portfolio['Cash'] = float(self.initial_capital)
        portfolio['Holdings'] = 0.0
        portfolio['Total'] = float(self.initial_capital)

        current_cash = float(self.initial_capital)
        current_shares = 0.0

        self.trades = [] # Track individual trades for metrics

        for index, row in self.data.iterrows():
            signal = row.get('Signal', 0)
            price = row['Close']

            # Simple assumption: We buy as much as we can with current cash, and sell all shares we hold
            # In a real system, we'd have position sizing logic (e.g., risk 2% of portfolio per trade)
            if signal == 1 and current_cash > price:
                # Buy
                shares_to_buy = current_cash // price
                cost = shares_to_buy * price

                current_cash -= cost
                current_shares += shares_to_buy

                self.trades.append({'Date': index, 'Type': 'Buy', 'Price': price, 'Shares': shares_to_buy})

            elif signal == -1 and current_shares > 0:
                # Sell
                revenue = current_shares * price
                current_cash += revenue

                self.trades.append({'Date': index, 'Type': 'Sell', 'Price': price, 'Shares': current_shares})

                current_shares = 0.0

            # Update Portfolio value at this timestep
            portfolio.loc[index, 'Cash'] = current_cash
            portfolio.loc[index, 'Holdings'] = current_shares * price
            portfolio.loc[index, 'Total'] = current_cash + (current_shares * price)

        self.portfolio = portfolio
        return portfolio

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculates performance metrics based on the executed backtest."""
        if not hasattr(self, 'portfolio'):
            raise ValueError("Must call run() before calculating metrics.")

        final_value = self.portfolio.iloc[-1]['Total']
        total_return = ((final_value - self.initial_capital) / self.initial_capital) * 100

        # Calculate Win Rate from closed trades
        wins = 0
        total_closed_trades = 0

        # We process trades in pairs (Buy then Sell)
        # Note: In a true system, we'd track average entry price, but this is a simplified view
        buy_price = 0.0

        for trade in self.trades:
            if trade['Type'] == 'Buy':
                buy_price = trade['Price']
            elif trade['Type'] == 'Sell' and buy_price > 0:
                total_closed_trades += 1
                if trade['Price'] > buy_price:
                    wins += 1
                buy_price = 0.0 # Reset

        win_rate = (wins / total_closed_trades * 100) if total_closed_trades > 0 else 0.0

        # Calculate benchmark (Buy & Hold)
        start_price = self.data.iloc[0]['Close']
        end_price = self.data.iloc[-1]['Close']
        benchmark_return = ((end_price - start_price) / start_price) * 100

        return {
            "Initial Capital": self.initial_capital,
            "Final Value": round(final_value, 2),
            "Total Return (%)": round(total_return, 2),
            "Benchmark Return (%)": round(benchmark_return, 2),
            "Total Trades": len(self.trades),
            "Closed Trades": total_closed_trades,
            "Win Rate (%)": round(win_rate, 2)
        }
