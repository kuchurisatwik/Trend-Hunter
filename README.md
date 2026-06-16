# Trend-Hunter: Algorithmic Crypto Trading Engine

An institutional-grade algorithmic trading framework designed to systematically capture momentum swings using WaveTrend, EMA200, and ADX, with advanced Chandelier Trailing Stops and partial Take-Profits.

## 🚀 The Journey: From Meme Coins to Universal Edge

We initially started this project attempting to trade high-volatility meme coins (PEPE, SHIB) on the 15-minute timeframe. However, after building a mathematically pure, infinite-precision backtesting engine, we uncovered the harsh reality of systematic trading:

1. **The Meme Coin Mirage:** Decimal-rounding issues were artificially inflating backtest profits on micro-cap coins. Once precision was fixed, the math proved that meme coins are too choppy for this logic.
2. **The Ablation Study:** We built a custom Ablation Engine (Versions A through E) to test 50 coins simultaneously across 1 full year. We discovered that adding Volume Expansion and deep WaveTrend pullbacks (Version D) drastically increased our Win Rate and Profit Factor.
3. **The Universal Edge DNA:** We deployed a Parallel Grid-Search Hyperparameter Optimizer over 45 million candles. The math pinpointed the exact parameters to maximize alpha: `EMA200`, `WaveTrend(10)`, `ADX(15)`, Breakeven at `1.2R`, and Partial Take-Profit at `2.5R`.
4. **The Goldilocks Assets:** A grueling 2-Year Stress Test revealed that Mid-cap AI and Layer-1 tokens (`FET`, `APT`) are the absolute perfect assets for this algorithm, while heavy mega-caps (`ETH`) are too slow.

## ⚙️ Features
- **Ablation Engine:** Toggle filters on/off to scientifically prove if an indicator actually works.
- **Hyperparameter Optimizer:** 4-core parallel grid search to dynamically find the best indicator combinations.
- **Advanced Dynamic Exits:** Risk 1% per trade. Moves to breakeven at 1.2R, secures 50% profit at 2.5R, and rides the runner using a 2.5x ATR Chandelier Trailing Stop.
- **Beautiful HTML Dashboard:** Visualizes massive 50-coin multi-year equity curves using Chart.js.

---

## 🛠 How to Use & Backtest

**1. Install Dependencies**
```bash
pip install pandas ccxt tqdm
```

**2. Run the Optimal Backtest**
Runs the heavily optimized 2-Year backtest on our most robust "All-Weather" coins (FET, ALGO, APT, ETH).
```bash
python run_final.py
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
python run_optimizer.py
```

---

## 📈 How to Start Live Trading

Currently, this repository is a **Historical Backtesting & Optimization Engine**. To deploy this mathematically proven edge into a live, real-time trading bot, follow these next steps:

1. **API Keys:** You will need to generate API Keys on Binance (or your preferred exchange) with Future/Spot Trading enabled.
2. **WebSocket Integration:** Replace `fetch_ohlcv` with a live WebSocket connection via `ccxt.pro` or `binance-connector` to stream 15-minute candles in real-time.
3. **Execution Engine:** Modify `engine.py` to route the `generate_signals` directly into an execution module that uses `ccxt.create_order()` to place real Long/Short orders, trigger Breakeven limits, and manage the Trailing Stops dynamically.
4. **Cloud Hosting:** Deploy the bot on a cheap AWS EC2 or DigitalOcean Droplet so it can run 24/7 without interruption.
