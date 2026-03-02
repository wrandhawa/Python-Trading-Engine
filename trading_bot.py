import os
import time
import logging
import datetime
from typing import List, Dict, Optional, Any

import numpy as np
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import robin_stocks.robinhood as r
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TradingBot")

class TradingBot:
    """
    Advanced Python Trading Engine.
    Implements a modular, object-oriented approach for strategy execution.
    """

    def __init__(self, symbols: List[str], rsi_period: int = 14, sma_fast: int = 10, sma_slow: int = 30):
        """
        Initializes the Trading Bot.

        Args:
            symbols (List[str]): List of stock ticker symbols to trade.
            rsi_period (int): Period for Relative Strength Index calculation.
            sma_fast (int): Period for the Fast Simple Moving Average.
            sma_slow (int): Period for the Slow Simple Moving Average.
        """
        self.symbols = symbols
        self.rsi_period = rsi_period
        self.sma_fast = sma_fast
        self.sma_slow = sma_slow

        # Load environment variables
        load_dotenv()
        self.username = os.getenv("ROBINHOOD_USERNAME")
        self.password = os.getenv("ROBINHOOD_PASSWORD")

        if not self.username or not self.password:
            logger.error("Robinhood credentials not found in environment variables.")
            raise ValueError("ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD must be set.")

        self._login()

        # State tracking
        self.positions = {symbol: False for symbol in self.symbols} # False = No position, True = Has position

    def _login(self) -> None:
        """Securely logs in to the Robinhood API."""
        try:
            logger.info("Attempting to log in to Robinhood...")
            # expiresIn=86400 (one day)
            r.login(
                username=self.username,
                password=self.password,
                expiresIn=86400,
                by_sms=True
            )
            logger.info("Successfully logged in to Robinhood.")
        except Exception as e:
            logger.error(f"Failed to log in to Robinhood: {e}")
            raise

    def fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Retrieves historical 1-minute interval data for the given symbol using yfinance.

        Args:
            symbol (str): The stock ticker symbol.

        Returns:
            Optional[pd.DataFrame]: A DataFrame containing historical data or None if an error occurs.
        """
        try:
            logger.info(f"Fetching historical data for {symbol}...")
            asset = yf.Ticker(symbol)
            # Get the past 2 days to ensure we have enough data points for slow SMAs/RSI
            start_date = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime('%Y-%m-%d')
            df = asset.history(start=start_date, interval='1m')

            if df.empty:
                logger.warning(f"No historical data returned for {symbol}.")
                return None

            # Clean up unneeded columns
            if 'Dividends' in df.columns:
                del df['Dividends']
            if 'Stock Splits' in df.columns:
                del df['Stock Splits']
            if 'Volume' in df.columns:
                del df['Volume']

            return df

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates trading indicators (RSI, Fast SMA, Slow SMA).

        Args:
            df (pd.DataFrame): Historical data DataFrame.

        Returns:
            pd.DataFrame: DataFrame with the new indicator columns appended.
        """
        if df is None or df.empty:
            return df

        try:
            logger.debug("Calculating technical indicators...")

            # Simple Moving Averages using pandas-ta
            df['Fast_SMA'] = ta.sma(df['Close'], length=self.sma_fast)
            df['Slow_SMA'] = ta.sma(df['Close'], length=self.sma_slow)

            # Relative Strength Index using pandas-ta
            df['RSI'] = ta.rsi(df['Close'], length=self.rsi_period)

            return df
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df

    def execute_trades(self, symbol: str, df: pd.DataFrame) -> None:
        """
        Evaluates the strategy logic and places buy/sell orders via Robinhood if conditions are met.

        Args:
            symbol (str): The stock ticker symbol.
            df (pd.DataFrame): DataFrame containing price data and indicators.
        """
        if df is None or df.empty or len(df) < max(self.sma_slow, self.rsi_period):
            logger.debug(f"Not enough data to calculate signals for {symbol}.")
            return

        try:
            # Look at the most recent completed period's data
            latest_data = df.iloc[-1]
            current_rsi = latest_data['RSI']
            fast_sma = latest_data['Fast_SMA']
            slow_sma = latest_data['Slow_SMA']

            if pd.isna(current_rsi) or pd.isna(fast_sma) or pd.isna(slow_sma):
                logger.debug(f"Indicators not fully calculated for {symbol}, skipping...")
                return

            # Check if we currently own the stock
            has_position = self.positions[symbol]
            # Optionally query real-time position from RH API to ensure accuracy
            # share_quantity = float(r.stocks.get_share_quantity(symbol) or 0)

            logger.info(f"[{symbol}] RSI: {current_rsi:.2f} | Fast SMA: {fast_sma:.2f} | Slow SMA: {slow_sma:.2f} | Position: {has_position}")

            # Trading Logic
            # 1. RSI strategy: Buy if oversold (<= 30) AND not holding position
            # 2. Moving Average strategy: Buy if Fast SMA > Slow SMA

            buy_signal = (current_rsi <= 30) or (fast_sma > slow_sma)
            sell_signal = (current_rsi >= 70) or (fast_sma < slow_sma)

            if buy_signal and not has_position:
                logger.info(f"*** BUY SIGNAL for {symbol} *** (RSI: {current_rsi:.2f}, Fast/Slow: {fast_sma:.2f}/{slow_sma:.2f})")
                self._place_order(symbol, "buy", 1)  # Buying 1 share for testing purposes
                self.positions[symbol] = True

            elif sell_signal and has_position:
                logger.info(f"*** SELL SIGNAL for {symbol} *** (RSI: {current_rsi:.2f}, Fast/Slow: {fast_sma:.2f}/{slow_sma:.2f})")
                # Retrieve actual share quantity before selling
                try:
                    positions = r.account.get_open_stock_positions()
                    shares_to_sell = 0
                    for pos in positions:
                        if r.stocks.get_symbol_by_url(pos['instrument']) == symbol:
                            shares_to_sell = float(pos['quantity'])
                            break

                    if shares_to_sell > 0:
                        self._place_order(symbol, "sell", shares_to_sell)
                    else:
                        logger.warning(f"Wanted to sell {symbol} but API returned 0 shares. Correcting internal state.")

                except Exception as e:
                    logger.error(f"Error checking position before selling {symbol}: {e}")

                self.positions[symbol] = False

            else:
                logger.debug(f"No actionable trade for {symbol}. Hold.")

        except Exception as e:
            logger.error(f"Error during strategy evaluation for {symbol}: {e}")

    def _place_order(self, symbol: str, side: str, quantity: float) -> None:
        """
        Helper method to place market orders safely.
        """
        try:
            logger.info(f"Placing {side.upper()} order for {quantity} shares of {symbol}...")
            # Uncomment the lines below to actually place orders in production:

            # if side.lower() == 'buy':
            #     order = r.orders.order_buy_market(symbol, quantity)
            # elif side.lower() == 'sell':
            #     order = r.orders.order_sell_market(symbol, quantity)
            # logger.info(f"Order result: {order}")

            logger.info(f"[SIMULATED] Successfully placed {side} order for {symbol}.")

        except Exception as e:
            logger.error(f"Failed to place {side} order for {symbol}: {e}")

    def run(self, interval_seconds: int = 60) -> None:
        """
        Main execution loop.

        Args:
            interval_seconds (int): Delay between iterations to prevent API rate limiting.
        """
        logger.info(f"Starting TradingBot loop for {self.symbols}...")

        try:
            while True:
                for symbol in self.symbols:
                    try:
                        # 1. Fetch data
                        df = self.fetch_data(symbol)
                        if df is None:
                            continue

                        # 2. Calculate indicators
                        df = self.calculate_indicators(df)

                        # 3. Evaluate and execute
                        self.execute_trades(symbol, df)

                    except Exception as e:
                        logger.error(f"Unexpected error processing {symbol}: {e}")

                # Sleep to respect rate limits and allow next 1-minute candle to form
                logger.debug(f"Sleeping for {interval_seconds} seconds...")
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("TradingBot stopped manually via KeyboardInterrupt.")

if __name__ == "__main__":
    # Example usage
    symbols_to_trade = ["AAPL", "TSLA"]
    try:
        bot = TradingBot(
            symbols=symbols_to_trade,
            rsi_period=14,
            sma_fast=10,
            sma_slow=30
        )
        # Check every 60 seconds
        bot.run(interval_seconds=60)
    except Exception as e:
        logger.error(f"Failed to initialize and run TradingBot: {e}")
