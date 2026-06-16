# Trend-Hunter: Algorithmic Crypto Trading Engine

An institutional-grade algorithmic trading framework designed to systematically capture momentum swings on the 15-minute timeframe. It utilizes a combination of moving averages, momentum oscillators, and volume expansion to trigger sniper-like entries, followed by dynamic partial-exits to maximize alpha.

---

## 🧠 How the Strategy Works

The strategy is built on the philosophy of "Trend Following on Pullbacks". It never buys the top of a rally; instead, it waits for the macro-trend to establish, waits for a micro-pullback, and then enters the exact moment momentum shifts back into the trend's direction.

### 1. The Entry Conditions (Long Example)
A Long trade is only triggered when **all 4 of these conditions** align simultaneously:

1. **Macro Trend (EMA 200):** The current price must be above the 200-period Exponential Moving Average, AND the EMA itself must be sloping upwards (price > EMA200 > EMA200 5 bars ago).
2. **Trend Strength (ADX > 15):** The Average Directional Index (ADX) must be above 15. This filters out sideways, choppy markets where trend-following strategies typically bleed capital.
3. **Deep Pullback (WaveTrend):** The fast WaveTrend line (WT1) must have recently dropped into negative territory (< 0). This proves the asset just had a healthy pullback. 
4. **Momentum Shift & Volume:** The fast WaveTrend line (WT1) must cross *above* the slow signal line (WT2), AND the current candle's volume must be strictly higher than the 50-period Volume Moving Average. This proves institutional volume is stepping in to buy the dip.

*(Short trades are the exact inverse)*

### 2. Dynamic Risk Management & Exits
Once in a trade, the engine uses an aggressive scale-out mechanism to protect capital while letting winners run.

- **Initial Stop Loss:** Placed at the recent Swing Low. Position sizing is calculated so exactly **1% of account equity** is risked.
- **Breakeven (1.2R):** The moment the trade reaches 1.2x the initial risk in profit, the Stop Loss is immediately moved to the Entry Price. It is now a "risk-free" trade.
- **Partial Take-Profit (2.5R):** Once the trade reaches 2.5x risk, the engine automatically closes **50% of the position**, securing locked-in profits.
- **Chandelier Runner:** The remaining 50% (the "Runner") is left open with no hard Take-Profit. Instead, the Stop Loss trails behind the price using a **2.5x ATR Chandelier Stop**. If the coin goes on a massive 30% parabolic run, the runner stays alive for the entire ride until the trend finally breaks.

---

## ⚙️ Core Architecture
- **`data/`**: CCXT integration for fetching historical OHLCV candles without API keys.
- **`indicators/`**: Pure Pandas implementations of WaveTrend, ADX, ATR, and Volume MAs.
- **`strategy/`**: The signal generator and position-sizing risk math.
- **`backtest/`**: The state-machine engine that processes Breakevens, Partials, and Chandelier trails candle-by-candle.
- **`scripts/`**: The executable runners for optimization, 50-coin massive backtests, and HTML dashboard generation.

---

## 🛠 How to Use & Backtest

**1. Install Dependencies**
```bash
pip install pandas ccxt tqdm
```

**2. Run the Optimal Backtest**
Runs the heavily optimized 2-Year backtest on our most robust "All-Weather" mid-cap coins (FET, ALGO, APT, ETH).
```bash
python -m scripts.run_final
```

**3. View the Dashboard**
Launch a local web server to view the rich HTML Dashboard with equity curves.
```bash
python -m http.server 8080
```
Open your browser to: `http://localhost:8080/dashboard/`

**4. Run the Optimizer**
Want to find new parameters for a different coin? Run the parallel hyperparameter optimizer:
```bash
python -m scripts.run_optimizer
```

---

## 📈 How to Start Live Trading

Currently, this repository is a **Historical Backtesting & Optimization Engine**. To deploy this mathematically proven edge into a live, real-time trading bot, follow these next steps:

1. **API Keys:** You will need to generate API Keys on Binance (or your preferred exchange) with Future/Spot Trading enabled.
2. **WebSocket Integration:** Replace `fetch_ohlcv` with a live WebSocket connection via `ccxt.pro` or `binance-connector` to stream 15-minute candles in real-time.
3. **Execution Engine:** Modify `engine.py` to route the `generate_signals` directly into an execution module that uses `ccxt.create_order()` to place real Long/Short orders, trigger Breakeven limits, and manage the Trailing Stops dynamically.
4. **Cloud Hosting:** Deploy the bot on a cheap AWS EC2 or DigitalOcean Droplet so it can run 24/7 without interruption.
