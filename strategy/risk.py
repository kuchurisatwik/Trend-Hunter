# ============================================
# strategy/risk.py — Dynamic ATR Position Sizing
# ============================================
import config

def calculate_position(entry_price, swing_level, atr, direction, account_balance=None):
    """
    Calculate position size and stop loss using ATR + Swing limits.
    """
    if account_balance is None:
        account_balance = config.ACCOUNT_SIZE

    risk_amount = account_balance * config.RISK_PER_TRADE

    if direction == "LONG":
        # Stop is the lower of Swing Low or 1.5 * ATR
        atr_stop = entry_price - (1.5 * atr)
        stop_loss = min(swing_level, atr_stop)
        
        # Enforce minimum distance to avoid noise
        min_stop = entry_price - (0.5 * atr)
        if stop_loss > min_stop:
            stop_loss = min_stop
            
        risk_per_unit = entry_price - stop_loss
        
    else:  # SHORT
        # Stop is the higher of Swing High or 1.5 * ATR
        atr_stop = entry_price + (1.5 * atr)
        stop_loss = max(swing_level, atr_stop)
        
        min_stop = entry_price + (0.5 * atr)
        if stop_loss < min_stop:
            stop_loss = min_stop
            
        risk_per_unit = stop_loss - entry_price

    if risk_per_unit <= 0:
        return None

    position_size = risk_amount / risk_per_unit

    return {
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "position_size": position_size,
        "risk_amount": risk_amount,
        "risk_per_unit": risk_per_unit,
        "initial_stop": stop_loss
    }
