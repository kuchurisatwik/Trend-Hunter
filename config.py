# ============================================
# config.py — All strategy settings in one place
# ============================================
# Change these values to customize the strategy.
# You don't need to touch any other file.
# ============================================


# ----- Coins to Backtest -----
# Only trade high-liquidity coins (avoid meme coins)
SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
]


# ----- Timeframe -----
# "15m" is recommended for beginners
# "5m" generates more signals but also more noise
TIMEFRAME = "15m"


# ----- Short Selling -----
# When True, the strategy will also take short positions.
ENABLE_SHORTS = True

# ----- Multi-Timeframe Mode (for 5m trading) -----
# When True, uses 15m trend + 5m entries
# When False, uses single 15m timeframe (recommended)
USE_5M_MODE = False
HTF_TIMEFRAME = "15m"   # Higher timeframe for trend filter


# ----- 4H EMA Alignment (longer-term trend) -----
# When True, only takes trades when 4H close > 4H EMA200
# This avoids buying during macro downtrends
USE_4H_TREND_FILTER = True
HTF_4H_TIMEFRAME = "4h"


# ----- EMA Settings -----
EMA_LENGTH = 200         # EMA period (200 is standard)
EMA_SLOPE_BARS = 5       # Number of bars to measure EMA slope


# ----- WaveTrend Settings -----
WT_CHANNEL_LENGTH = 10   # WaveTrend channel period
WT_AVERAGE_LENGTH = 21   # WaveTrend average period
WT_PULLBACK_LEVEL = 0    # WT1 must cross +/- this level for a valid pullback

# ----- Regime & Volatility Filters -----
ADX_LENGTH = 14          # ADX period
ADX_THRESHOLD = 15       # ADX must be above this (trending market)
ATR_LENGTH = 14          # ATR period for stop loss and trailing


# ----- Breakout Settings -----
SWING_HIGH_BARS = 5      # Number of bars for swing high/low lookback
                         # 5 bars on 15m = 1.25 hours


# ----- Volume Settings -----
VOLUME_MA_LENGTH = 50    # Volume moving average period


# ----- Risk & Exits -----
ACCOUNT_SIZE = 1000      # Starting account balance in USDT
RISK_PER_TRADE = 0.01    # Risk 1% of account per trade

# Advanced Dynamic Exits
BREAKEVEN_R = 1.2        # Move stop to breakeven at +1.2R profit
PARTIAL_TP_R = 2.5       # Take partial profit at +2.5R
PARTIAL_TP_PCT = 0.5     # Close 50% of the position at TP
CHANDELIER_ATR_MULT = 2.5 # Trailing stop distance for the runner (2.5 * ATR)


# ----- Data Settings -----
LOOKBACK_DAYS = 730      # How many days of historical data to fetch
EXCHANGE_ID = "binance"  # Exchange to fetch data from


# ----- Output -----
RESULTS_DIR = "results"  # Folder where results are saved
