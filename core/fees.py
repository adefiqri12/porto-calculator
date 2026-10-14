"""Fee models and liquidation distance.

Constants are taken from the two reference reports in archive/trading-simulation.
"""
FUTURES_TAKER_PCT = 0.05      # per side
FUTURES_FUNDING_PCT = 0.03    # per trade, on notional
SPOT_PCT = 0.5                # per side
SPOT_FEE_FLOOR = 0.95         # USD, per transaction, applies even to tiny trades


def percent_fee(notional: float, pct: float, sides: int = 2) -> float:
    """Flat percentage fee, charged on each side."""
    return notional * pct / 100.0 * sides


def min_fee(notional: float, pct: float, floor: float, sides: int = 2) -> float:
    """Percentage fee with a per-transaction floor. The floor dominates small trades."""
    return max(notional * pct / 100.0, floor) * sides


def futures_fee(notional: float) -> float:
    """Binance futures: taker fee both sides plus one funding payment."""
    return notional * (FUTURES_TAKER_PCT / 100.0 * 2 + FUTURES_FUNDING_PCT / 100.0)


def spot_fee(notional: float) -> float:
    """fomo.family spot: 0.5% per side with a $0.95 minimum per transaction."""
    return min_fee(notional, SPOT_PCT, SPOT_FEE_FLOOR, sides=2)


def liquidation_price(entry: float, leverage: float, side: str = "long") -> float:
    """Approximate liquidation price. Isolated margin, ignoring maintenance margin."""
    if leverage < 1:
        raise ValueError("leverage must be >= 1")
    if side == "long":
        return entry * (1.0 - 1.0 / leverage)
    if side == "short":
        return entry * (1.0 + 1.0 / leverage)
    raise ValueError("side must be 'long' or 'short'")


def liquidation_distance_pct(leverage: float) -> float:
    """Price move that liquidates a position, as a percentage (always negative)."""
    if leverage < 1:
        raise ValueError("leverage must be >= 1")
    return -100.0 / leverage
