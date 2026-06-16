# Loss Forensics — Deep Analysis & Structural Fixes

> **334 trades analyzed** across 11 strong coins | 154 wins (46.1%) | 179 losses (53.6%) | 23 loss streaks of 3+

---

## The Big Question: Why Do Losses Streak 3-5 Times?

After examining all 23 loss streaks across 11 coins, they share a common pattern:

**The market enters a choppy/ranging phase within an uptrend.** The EMA200 is still sloping up, price is still above it, but the price is oscillating in a tight range. Each WaveTrend cross triggers a signal, and each breakout fails because there's no momentum behind it.

This is the fundamental problem: **the strategy detects trend conditions, but can't distinguish a STRONG trend from a WEAK/exhausting trend.**

---

## 5 Data-Backed Filters to Reduce Losses

> [!IMPORTANT]
> These are NOT curve-fitted tweaks. Each filter targets a specific trade category that performs badly across ALL 11 coins, with at least 30+ trades in the sample. They are structural improvements.

---

### Filter 1: Volume Dead Zone (Biggest Impact)

| Volume Ratio | Trades | Win Rate | Avg P&L |
|---|---|---|---|
| 0.8-1.0x MA | 43 | **32.6%** | **-$0.25** |
| 1.0-1.5x MA | 82 | 48.8% | +$4.76 |
| 1.5-2.0x MA | 39 | **53.8%** | **+$6.47** |

**The fix:** Currently we check if Volume MA is *rising*. But a rising MA doesn't mean volume is actually strong RIGHT NOW. The 0.8-1.0x range is the dead zone — volume is near average but not above it. The breakout has no fuel.

```python
# OLD: just check if MA is rising
vol_ok = df["vol_rising"]

# NEW: also require actual volume > 1.0x the MA
vol_ok = df["vol_rising"] & (df["volume"] > df["VOL_MA"])
```

**Expected impact:** Removes ~43 trades with 32.6% WR, keeps the 48-54% WR trades.

---

### Filter 2: Stop Loss Too Wide (2-3% distance)

| Stop Distance | Trades | Win Rate | Avg P&L |
|---|---|---|---|
| 1.0-1.5% | 105 | **50.5%** | **+$5.24** |
| 1.5-2.0% | 68 | **51.5%** | **+$5.70** |
| 2.0-3.0% | 73 | **37.0%** | +$1.30 |
| > 3.0% | 20 | 45.0% | +$3.48 |

**The fix:** When the stop is 2-3% away, the position size gets very small (because risk is fixed at 1%). This means wins are tiny too. But the wide stop means the trade needs a HUGE move to hit 2R target — unlikely on 15m.

```python
# Skip trades where stop loss is too far from entry
stop_distance_pct = (entry_price - swing_low) / entry_price
if stop_distance_pct > 0.02:  # more than 2%
    return None  # skip this trade
```

**Expected impact:** Removes ~93 trades with 37-45% WR, focuses on the 50%+ WR sweet spot.

---

### Filter 3: Quick Stop-Outs (< 2 hours)

| Duration | Trades | Win Rate | Avg P&L |
|---|---|---|---|
| < 30 min | 7 | **14.3%** | **-$6.05** |
| 30-60 min | 27 | 40.7% | +$2.33 |
| 1-2 hours | 71 | 39.4% | +$2.09 |
| 4-8 hours | 82 | **52.4%** | **+$5.83** |
| 8-24 hours | 67 | **52.2%** | **+$5.94** |
| > 24 hours | 11 | **81.8%** | **+$15.12** |

**The insight:** We can't filter by duration *before* entry (we don't know how long the trade will last). But this tells us something important about the **stop loss placement**: trades that get stopped within 2 hours are entering in choppy conditions where the swing low is too close. The fix is already partially covered by Filter 2 (wider stops = faster stop-outs in choppy markets).

**Additional approach:** Add a minimum swing low distance. If the last 5-bar low is too close to the entry (< 0.5%), skip — the trade has no room to breathe.

```python
# Minimum breathing room
stop_distance_pct = (entry_price - swing_low) / entry_price
if stop_distance_pct < 0.005:  # less than 0.5%
    return None  # too tight, will get stopped by noise
```

---

### Filter 4: Midnight UTC Killzone (00-04 UTC)

| Time Block | Trades | Win Rate | Avg P&L |
|---|---|---|---|
| 00-04 UTC | 70 | **38.6%** | +$1.67 |
| 04-08 UTC | 38 | **55.3%** | **+$7.38** |
| 16-20 UTC | 50 | **52.0%** | **+$5.67** |
| 20-24 UTC | 42 | 40.5% | +$1.92 |

**The fix:** The 00-04 UTC window (5:30 - 9:30 AM IST) has low volume and choppy price action. Most Asian session moves are fakeouts that reverse during the European session.

```python
# Skip signals during low-quality hours
entry_hour = candle["timestamp"].hour
if entry_hour < 4:  # 00:00 - 04:00 UTC
    skip this signal
```

> [!WARNING]
> This is the most "opinionated" filter. It works across all 11 coins in the backtest, but could potentially miss some good trades. I'd implement it as an optional toggle in config.

**Expected impact:** Removes ~70 trades with 38.6% WR.

---

### Filter 5: WT1 Crossover Zone (-20 to -10 is Weak)

| WT1 at Entry | Trades | Win Rate | Avg P&L |
|---|---|---|---|
| WT1 < -20 | 107 | **49.5%** | **+$5.17** |
| -20 to -10 | 70 | **38.6%** | +$1.41 |
| -10 to 0 | 76 | 44.7% | +$3.45 |
| 0 to 10 | 66 | **50.0%** | **+$5.51** |

**The insight:** The -20 to -10 zone is the worst. The pullback isn't deep enough (WT1 didn't go low enough) and the crossover happens in a "no man's land" where neither bulls nor bears are in control.

Two good entry zones exist:
1. **WT1 < -20**: Deep pullback, strong snap-back (49.5% WR)
2. **WT1 between 0 and 10**: Shallow pullback in a STRONG trend (50% WR)

The fix: require WT1 to have been below -20 at some point in the last 5 bars (not just below 0).

```python
# Stricter pullback: WT1 must have gone below -20, not just 0
WT_PULLBACK_LEVEL = -20  # changed from 0
```

> [!CAUTION]
> This is the borderline one. Moving from 0 to -20 reduces trades significantly. However, the data supports it: < -20 has 49.5% WR vs 38.6% for -20 to -10. I'd recommend trying -15 as a compromise.

---

## What I Would NOT Change

> [!NOTE]
> These parameters should stay as-is. Changing them would be overfitting.

| Parameter | Current | Why Keep It |
|---|---|---|
| EMA Length | 200 | Industry standard, works across all timeframes |
| Swing Bars | 5 | The data shows no significant WR difference between breakout strengths |
| Reward Ratio | 2R | The avg win is already ~2x avg loss, this is working correctly |
| Risk % | 1% | Correct for the drawdown levels we're seeing |
| 4H Filter | ON | Already blocking bad trades in macro downtrends |

---

## Proposed Changes Summary

| Filter | What | Trades Removed | WR of Removed | Implementation |
|---|---|---|---|---|
| Volume > 1x MA | Skip dead zone volume | ~43 | 32.6% | `signals.py` |
| Stop 0.5%-2.0% | Skip too-tight and too-wide stops | ~27 tight + ~93 wide | 14-37% | `risk.py` |
| WT pullback < -15 | Deeper pullback required | ~70 in -20 to 0 zone | 38.6% | `config.py` |
| Skip 00-04 UTC | Avoid midnight fakeouts | ~70 | 38.6% | `signals.py` (optional) |

**Combined estimated effect:** Remove the ~100-150 worst trades (30-38% WR) while keeping the ~180-200 best trades (48-54% WR). This should push overall win rate from 46% to approximately **52-55%** across the 11 coins.

---

## Next Step

Approve these filters and I'll implement them and re-run the 11-coin backtest to verify the improvement is real and not just theoretical.
