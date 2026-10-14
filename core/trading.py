"""Trading expectation, break-even, profit factor, per-trade Sharpe.

win_rate arguments are decimal fractions in [0, 1], not percentages.
"""
import math


def _require_nonzero(reward: float, risk: float) -> None:
    if reward == 0 and risk == 0:
        raise ValueError("reward and risk cannot both be zero")


def expected_value(win_rate: float, reward: float, risk: float) -> float:
    return win_rate * reward - (1.0 - win_rate) * risk


def break_even_win_rate(reward: float, risk: float) -> float:
    """Win rate at which expected value is zero. Equals risk / (risk + reward)."""
    _require_nonzero(reward, risk)
    return risk / (risk + reward)


def profit_factor(win_rate: float, reward: float, risk: float) -> float:
    """Gross wins divided by gross losses."""
    _require_nonzero(reward, risk)
    return (win_rate * reward) / ((1.0 - win_rate) * risk)


def std_per_trade(win_rate: float, reward: float, risk: float) -> float:
    ev = expected_value(win_rate, reward, risk)
    var = win_rate * (reward - ev) ** 2 + (1.0 - win_rate) * (-risk - ev) ** 2
    return math.sqrt(var)


def sharpe_per_trade(win_rate: float, reward: float, risk: float, fee: float = 0.0) -> float:
    """Per-trade Sharpe, deliberately NOT annualised.

    Not annualising is what reproduces the reference reports (A = 0.590,
    C = 0.691 at 50% win rate). A degenerate distribution (0% or 100% win
    rate) has zero variance; return 0.0 rather than dividing by zero.
    """
    sd = std_per_trade(win_rate, reward, risk)
    if sd == 0.0:
        return 0.0
    return (expected_value(win_rate, reward, risk) - fee) / sd


def net_profit(win_rate: float, reward: float, risk: float, fee: float, trades: int) -> float:
    return trades * (expected_value(win_rate, reward, risk) - fee)


def gross_profit(win_rate: float, reward: float, risk: float, trades: int) -> float:
    return trades * expected_value(win_rate, reward, risk)
