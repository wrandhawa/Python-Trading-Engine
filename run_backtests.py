import yfinance as yf
import pandas as pd
import datetime
from typing import Dict, Any

from backtester import Backtester, RSIMomentumStrategy, SMACrossoverStrategy

def fetch_historical_data(symbol: str, years: int = 5) -> pd.DataFrame:
    """Fetches years of daily historical data for the given symbol."""
    print(f"Downloading {years} years of historical data for {symbol}...")
    asset = yf.Ticker(symbol)

    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=years*365)

    df = asset.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval='1d')
    return df

def print_metrics(strategy_name: str, metrics: Dict[str, Any]) -> None:
    """Pretty prints the results of a backtest."""
    print(f"\n{'='*40}")
    print(f"Strategy: {strategy_name}")
    print(f"{'='*40}")
    for key, value in metrics.items():
        print(f"{key}: {value}")
    print(f"{'='*40}")

def main():
    # We will test on SPY (S&P 500 ETF) as it's a standard benchmark
    symbol = "SPY"

    # Download 3 years of daily data
    data = fetch_historical_data(symbol, years=3)

    if data.empty:
        print("Failed to download data. Exiting.")
        return

    initial_capital = 10000.0

    # 1. Test RSI Momentum Strategy
    rsi_strategy = RSIMomentumStrategy(period=14, oversold=30, overbought=70)
    rsi_backtester = Backtester(data, strategy=rsi_strategy, initial_capital=initial_capital)
    rsi_backtester.run()
    print_metrics("RSI Momentum (14, 30/70)", rsi_backtester.calculate_metrics())

    # 2. Test SMA Crossover Strategy
    sma_strategy = SMACrossoverStrategy(fast_period=50, slow_period=200) # Golden/Death Cross
    sma_backtester = Backtester(data, strategy=sma_strategy, initial_capital=initial_capital)
    sma_backtester.run()
    print_metrics("SMA Crossover (50, 200)", sma_backtester.calculate_metrics())

if __name__ == "__main__":
    main()
