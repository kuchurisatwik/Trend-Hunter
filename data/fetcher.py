# ============================================
# data/fetcher.py — Download OHLCV candle data
# ============================================
# Uses ccxt to pull free data from Binance.
# No API key needed for historical candle data.
# ============================================

import os
import time
import pandas as pd
import ccxt

# Import settings from config
import config


def fetch_ohlcv(symbol, timeframe, lookback_days=None):
    """
    Download OHLCV (Open, High, Low, Close, Volume) candle data.

    Args:
        symbol:        Trading pair like "BTC/USDT"
        timeframe:     Candle size like "15m" or "5m"
        lookback_days: How many days of history to fetch

    Returns:
        pandas DataFrame with columns:
        timestamp, open, high, low, close, volume
    """

    if lookback_days is None:
        lookback_days = config.LOOKBACK_DAYS

    # Create exchange connection (no API key needed)
    exchange = ccxt.binance({
        "enableRateLimit": True,   # Respect rate limits
    })

    # Calculate start time in milliseconds
    since = exchange.milliseconds() - (lookback_days * 24 * 60 * 60 * 1000)

    print(f"  Fetching {symbol} {timeframe} data ({lookback_days} days)...")

    # Binance returns max 1000 candles per request
    # We need to loop to get all the data
    all_candles = []
    fetch_since = since

    while True:
        # Fetch a batch of candles
        candles = exchange.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since=fetch_since,
            limit=1000,
        )

        # No more data
        if len(candles) == 0:
            break

        all_candles.extend(candles)

        # Move to after the last candle we got
        fetch_since = candles[-1][0] + 1

        # If we got less than 1000, we've reached the end
        if len(candles) < 1000:
            break

        # Small delay to be nice to the API
        time.sleep(0.1)

    # Convert to DataFrame
    df = pd.DataFrame(
        all_candles,
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )

    # Convert timestamp to readable datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    # Remove duplicates (just in case)
    df = df.drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    if len(df) == 0:
        print(f"  Got 0 candles for {symbol}")
        return df

    print(f"  Got {len(df)} candles ({df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]})")

    return df


def fetch_and_cache(symbol, timeframe, lookback_days=None):
    """
    Fetch data and save to CSV so we don't re-download every time.

    If the CSV already exists and is recent, load from disk instead.

    Args:
        symbol:        Trading pair like "BTC/USDT"
        timeframe:     Candle size like "15m"
        lookback_days: How many days of history

    Returns:
        pandas DataFrame with OHLCV data
    """

    if lookback_days is None:
        lookback_days = config.LOOKBACK_DAYS

    # Create results directory if it doesn't exist
    os.makedirs(config.RESULTS_DIR, exist_ok=True)

    # Create a filename like "results/BTCUSDT_15m.csv"
    safe_symbol = symbol.replace("/", "")
    cache_file = os.path.join(config.RESULTS_DIR, f"{safe_symbol}_{timeframe}.csv")

    # Check if cached file exists and is less than 1 hour old
    if os.path.exists(cache_file):
        file_age_seconds = time.time() - os.path.getmtime(cache_file)
        one_hour = 3600

        if file_age_seconds < one_hour:
            print(f"  Loading cached data from {cache_file}")
            df = pd.read_csv(cache_file, parse_dates=["timestamp"])
            return df

    # Fetch fresh data
    df = fetch_ohlcv(symbol, timeframe, lookback_days)

    # Save to CSV
    df.to_csv(cache_file, index=False)
    print(f"  Saved to {cache_file}")

    return df
