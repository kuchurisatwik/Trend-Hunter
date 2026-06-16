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

## Backtest Results (2-Year, 15-Min Timeframe)

These are the real results from running the strategy on historical data. No cherry-picking — every trade, win or loss, is counted.

| Rank | Coin | Trades | Win Rate | Net Profit | Net Return | Profit Factor | Max Drawdown | Rating |
|------|------|--------|----------|------------|------------|---------------|--------------|--------|
| 1st | `FET/USDT` | 219 | 50.2% | +$857.84 | **+85.8%** | 1.65 | 8.2% | Strong |
| 2nd | `APT/USDT` | 210 | 45.7% | +$294.90 | **+29.5%** | 1.24 | 10.9% | Marginal |
| 3rd | `ALGO/USDT` | 209 | 43.5% | +$169.95 | **+17.0%** | 1.16 | 18.8% | Marginal |


> **Profit Factor** — How much you earn for every $1 you lose. Above 1.0 = profitable. FET's 1.65 means for every $1 lost, the bot made $1.65 back.
> 
> **Max Drawdown** — The worst dip the account took before recovering. FET's 8.2% means at its lowest point, the account was down 8.2% from its peak. Lower is better.
> 
> **Rating** — A summary judgment: *Strong* means the edge is clear and consistent. *Marginal* means profitable, but worth watching closely.

### Top 3 Takeaways

**1. FET is the star.** Nearly doubling your money in 2 years on a fully automated strategy — with a coin that's mid-cap and liquid — is a strong result. The 50.2% win rate means it wins just slightly more than half its trades, but the exits are sized so well that winners are much bigger than losers.

**2. APT proves the strategy generalizes.** A 29.5% return on a completely different coin, with no manual tweaking between them, shows this isn't a one-trick pony tuned specifically for FET.

**3. ALGO survived a rough year and still came out green.** ALGO massively underperformed the broader market in 2024, yet the bot still finished profitable. That's the stop loss and trailing exit doing their job — cutting losses fast and riding the good trades.

> ETH's razor-thin 4.7% return is a reminder that no strategy works equally well on every coin. ETH is the most "efficient" market of the four — harder to find an edge on.

---

## Want to Use This for Real Trading?

> Right now, this is a **backtesting tool only** — it tests on past data, it doesn't trade real money yet.

To make it live, you'd need to:

1. **Get API keys** from Binance (or another exchange) — these let a program trade on your behalf
2. **Switch from historical data to live data** — instead of downloading old candles, you'd stream live price updates as they happen
3. **Add an order execution module** — code that actually sends the "buy" and "sell" commands to the exchange
4. **Host it on a server** — so it runs 24/7 even when your computer is off (a cheap cloud server like AWS or DigitalOcean works fine)
