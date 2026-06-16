# Trend-Hunter: A Crypto Trading Bot

A program that automatically buys and sells crypto on your behalf by spotting the right moment to jump into a trend — and knowing when to walk away with your profits.

---

## What Does This Bot Actually Do?

Think of it like a patient fisherman. It doesn't throw the line in whenever it feels like it. It watches the water, waits for the exact right current, *then* casts.

The core idea: **don't buy when a coin is already flying — wait for it to dip, then buy the moment it starts climbing again.**

---

## How It Decides When to Buy

Before placing any trade, the bot has to tick **all 4 boxes** at the same time:

**1. Is the coin actually trending upward?**
It checks a line called the "200 EMA" — basically a smoothed-out average of the last 200 candles. If the price is above this line *and* the line itself is pointing upward, we're in an uptrend. Good sign.

**2. Is the trend strong enough to bother with?**
A measurement called ADX tells us how strong the trend is. If it's below 15, the market is just moving sideways and randomly — the bot ignores it entirely. Sideways markets are where trend-following strategies lose money.

**3. Has there been a real pullback?**
A tool called WaveTrend acts like a speedometer for momentum. The bot waits until this speedometer dips into negative territory — proof the coin just had a healthy "rest" before the next push up.

**4. Is big money stepping back in?**
The bot waits for the WaveTrend speedometer to flip back upward *while* the current candle's trading volume is higher than the 50-candle average. High volume + momentum flip = institutions buying the dip. That's our signal.

> *(For short/sell trades, it's all the exact opposite.)*

---

## How It Protects Your Money Once You're In a Trade

This is where it gets smart. Instead of just setting a fixed "sell here" target, the bot manages the trade in stages:

| Stage | When It Triggers | What Happens |
|-------|-----------------|--------------|
| **Stop Loss** | Immediately after entry | Exits if you'd lose more than 1% of your account |
| **Move to Breakeven** | At 1.2x your risk | Stop loss moves to entry price — you can't lose anymore |
| **Take Half the Profit** | At 2.5x your risk | Sells 50% of your position, locking in real cash |
| **Let the Runner Ride** | After the 50% is sold | Trailing stop follows price up; stays in until trend breaks |

---

## How the Code is Organized

You don't need to touch most of this, but here's what each folder does:

- **`data/`** — Downloads historical price data from exchanges (no account needed)
- **`indicators/`** — The math behind WaveTrend, ADX, ATR, and Volume averages
- **`strategy/`** — The logic that reads all the indicators and says "buy" or "don't buy"
- **`backtest/`** — A simulator that replays years of past data to see how the strategy would have performed, trade by trade
- **`scripts/`** — The buttons you actually press to run things

---

## How to Run It

### Step 1 — Install the required tools

Open your terminal and paste this:

```bash
pip install pandas ccxt tqdm
```

### Step 2 — Run the main backtest

Tests the strategy on 4 well-performing coins (FET, ALGO, APT, ETH) over the last 2 years:

```bash
python -m scripts.run_final
```

### Step 3 — View the results dashboard

Start a local web server:

```bash
python -m http.server 8080
```

Then open your browser and go to: `http://localhost:8080/dashboard/`

You'll see charts, equity curves, and trade history.

### Step 4 (Optional) — Find the best settings for a new coin

```bash
python -m scripts.run_optimizer
```

This automatically tests thousands of parameter combinations to find what works best.

---

## Want to Use This for Real Trading?

> Right now, this is a **backtesting tool only** — it tests on past data, it doesn't trade real money yet.

To make it live, you'd need to:

1. **Get API keys** from Binance (or another exchange) — these let a program trade on your behalf
2. **Switch from historical data to live data** — instead of downloading old candles, you'd stream live price updates as they happen
3. **Add an order execution module** — code that actually sends the "buy" and "sell" commands to the exchange
4. **Host it on a server** — so it runs 24/7 even when your computer is off (a cheap cloud server like AWS or DigitalOcean works fine)
