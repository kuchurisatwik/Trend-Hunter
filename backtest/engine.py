# ============================================
# backtest/engine.py — Advanced Long/Short Engine
# ============================================
# Handles partial exits (50% at 2R), Breakeven stops,
# and Chandelier trailing exits for both Longs & Shorts.
# ============================================

import os
import json
import pandas as pd
import numpy as np
import config
from strategy.risk import calculate_position

def run_backtest(df, symbol, save_files=True):
    balance = config.ACCOUNT_SIZE
    position = None
    trades = []
    equity_curve = []

    print(f"\n  Running advanced backtest for {symbol}...")

    for i in range(len(df)):
        row = df.iloc[i]
        
        # --- MANAGE OPEN POSITION ---
        if position is not None:
            dir_mult = 1 if position["direction"] == "LONG" else -1
            
            # Update Trailing Stop (Chandelier) if past breakeven
            if position["state"] in ["BE", "RUNNER"]:
                atr = row["ATR"]
                if position["direction"] == "LONG":
                    # Chandelier: Highest High - 2.5 ATR
                    trail_level = row["high"] - (config.CHANDELIER_ATR_MULT * atr)
                    if trail_level > position["stop_loss"]:
                        position["stop_loss"] = trail_level
                else:
                    # Chandelier: Lowest Low + 2.5 ATR
                    trail_level = row["low"] + (config.CHANDELIER_ATR_MULT * atr)
                    if trail_level < position["stop_loss"]:
                        position["stop_loss"] = trail_level

            # Check Stop Loss Hit
            stop_hit = False
            if position["direction"] == "LONG" and row["low"] <= position["stop_loss"]:
                stop_hit = True
            elif position["direction"] == "SHORT" and row["high"] >= position["stop_loss"]:
                stop_hit = True

            if stop_hit:
                exit_price = position["stop_loss"]
                pnl = (exit_price - position["entry_price"]) * position["current_size"] * dir_mult
                balance += pnl
                
                # Determine result string
                if position["state"] == "INITIAL":
                    res = "LOSS"
                elif position["state"] == "BE":
                    res = "BREAKEVEN"
                else:
                    res = "RUNNER_CLOSED"

                trades.append(_create_trade_record(position, row["timestamp"], exit_price, pnl, res, balance))
                position = None
                
            # Check Scale-Outs / State Changes (if not stopped out)
            if position is not None:
                current_r = ((row["close"] - position["entry_price"]) * dir_mult) / position["risk_per_unit"]
                
                # 1. Move to Breakeven
                if position["state"] == "INITIAL" and current_r >= config.BREAKEVEN_R:
                    position["stop_loss"] = position["entry_price"]
                    position["state"] = "BE"
                    
                # 2. Take Partial Profit
                if position["state"] in ["INITIAL", "BE"] and current_r >= config.PARTIAL_TP_R:
                    # Close 50%
                    close_size = position["initial_size"] * config.PARTIAL_TP_PCT
                    exit_price = position["entry_price"] + (config.PARTIAL_TP_R * position["risk_per_unit"] * dir_mult)
                    pnl = (exit_price - position["entry_price"]) * close_size * dir_mult
                    balance += pnl
                    
                    trades.append(_create_trade_record(position, row["timestamp"], exit_price, pnl, "PARTIAL_TP", balance, size_closed=close_size))
                    
                    position["current_size"] -= close_size
                    position["state"] = "RUNNER"
                    position["stop_loss"] = position["entry_price"] # ensure BE

        # --- CHECK FOR NEW ENTRY ---
        if position is None:
            if row.get("signal_long", False):
                pos = calculate_position(row["close"], row["swing_low"], row["ATR"], "LONG", balance)
            elif row.get("signal_short", False):
                pos = calculate_position(row["close"], row["swing_high"], row["ATR"], "SHORT", balance)
            else:
                pos = None

            if pos is not None:
                position = {
                    "direction": pos["direction"],
                    "entry_time": row["timestamp"],
                    "entry_price": pos["entry_price"],
                    "stop_loss": pos["stop_loss"],
                    "initial_stop": pos["initial_stop"],
                    "initial_size": pos["position_size"],
                    "current_size": pos["position_size"],
                    "risk_per_unit": pos["risk_per_unit"],
                    "state": "INITIAL" # INITIAL, BE, RUNNER
                }

        equity_curve.append({
            "timestamp": str(row["timestamp"]),
            "balance": round(balance, 2),
        })

    # Close open position at end
    if position is not None:
        last_row = df.iloc[-1]
        exit_price = last_row["close"]
        dir_mult = 1 if position["direction"] == "LONG" else -1
        pnl = (exit_price - position["entry_price"]) * position["current_size"] * dir_mult
        balance += pnl
        trades.append(_create_trade_record(position, last_row["timestamp"], exit_price, pnl, "OPEN", balance))

    summary = _calculate_summary(trades, balance)
    if save_files:
        _save_results(trades, equity_curve, summary, symbol)

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "summary": summary,
    }

def _create_trade_record(pos, exit_time, exit_price, pnl, result, balance, size_closed=None):
    size = size_closed if size_closed else pos["current_size"]
    return {
        "direction": pos["direction"],
        "entry_time": str(pos["entry_time"]),
        "exit_time": str(exit_time),
        "entry_price": pos["entry_price"],
        "exit_price": exit_price,
        "position_size": size,
        "pnl": pnl,
        "result": result,
        "balance_after": balance
    }

def _calculate_summary(trades, final_balance):
    if not trades:
        return {"total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0, "total_pnl": 0, "final_balance": final_balance, "return_pct": 0, "profit_factor": 0, "max_drawdown_pct": 0}

    # Group trades by entry_time to count "deals" instead of individual partial exits
    deals = {}
    for t in trades:
        k = t["entry_time"]
        if k not in deals:
            deals[k] = {"pnl": 0, "dir": t["direction"]}
        deals[k]["pnl"] += t["pnl"]

    wins = [d for d in deals.values() if d["pnl"] > 0]
    losses = [d for d in deals.values() if d["pnl"] < 0]
    
    total_pnl = sum(d["pnl"] for d in deals.values())
    gross_profit = sum(d["pnl"] for d in wins)
    gross_loss = abs(sum(d["pnl"] for d in losses))
    
    pf = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
    
    # Max DD
    peak = config.ACCOUNT_SIZE
    max_dd = 0
    running = config.ACCOUNT_SIZE
    
    for t in trades: # Use individual trades for DD to be precise
        running += t["pnl"]
        if running > peak: peak = running
        dd = (peak - running) / peak * 100
        if dd > max_dd: max_dd = dd

    return {
        "total_trades": len(deals),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(deals) * 100, 1) if deals else 0,
        "total_pnl": round(total_pnl, 2),
        "final_balance": round(final_balance, 2),
        "return_pct": round((final_balance - config.ACCOUNT_SIZE) / config.ACCOUNT_SIZE * 100, 1),
        "profit_factor": round(pf, 2),
        "max_drawdown_pct": round(max_dd, 1),
        "avg_win": round(gross_profit / len(wins), 2) if wins else 0,
        "avg_loss": round(gross_loss / len(losses), 2) if losses else 0,
    }

def _save_results(trades, equity_curve, summary, symbol):
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    safe_symbol = symbol.replace("/", "")
    if trades:
        pd.DataFrame(trades).to_csv(os.path.join(config.RESULTS_DIR, f"trades_{safe_symbol}.csv"), index=False)
    if equity_curve:
        pd.DataFrame(equity_curve).to_csv(os.path.join(config.RESULTS_DIR, f"equity_{safe_symbol}.csv"), index=False)

def save_dashboard_data(all_results):
    """Save combined results as JSON for the HTML dashboard."""
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    dashboard_data = {}
    for symbol, result in all_results.items():
        safe_symbol = symbol.replace("/", "")
        dashboard_data[safe_symbol] = {
            "summary": result["summary"],
            "trades": result["trades"],
            "equity_curve": result["equity_curve"],
        }
    json_path = os.path.join(config.RESULTS_DIR, "dashboard_data.json")
    with open(json_path, "w") as f:
        json.dump(dashboard_data, f, indent=2)
    print(f"\n  Dashboard data saved to {json_path}")
