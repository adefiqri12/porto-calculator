"""Reference implementation of the three archived-report strategies.

This module exists to prove the port is faithful: ``tests/test_golden.py``
checks these functions against the numbers scraped out of the HTML reports in
``archive/trading-simulation``. It is NOT used by the app any more. The
Simulate tab no longer offers strategies A/B/C; it takes manual inputs and runs
``core/mc.py``. ``core/presets.py`` still backs the Trading tab's quick-fill
dropdown.

The three sizing models:

- fixed:      constant $2 margin regardless of account size (strategies A, C)
- percent:    margin = pct% of the *initial* capital, constant notional per trade
- compounding: margin = pct% of *current* capital, so P&L is multiplicative (B)

Fee per trade follows the notional, so it is constant for fixed sizing and
proportional to capital for the percentage models.
"""
from core.fees import futures_fee
from core.presets import PRESETS
from core.trading import expected_value, sharpe_per_trade

BASE_MARGIN = 2.0          # the $2 reference margin from the reports
DEFAULT_LEVERAGE = 10.0
DEFAULT_SIZING_PCT = 2.0

# Futures fee on the $20 notional of a $2 margin at 10x: futures_fee(20) == 0.026
FIXED_FEE_PER_TRADE = futures_fee(BASE_MARGIN * DEFAULT_LEVERAGE)

# Fee as a fraction of account equity under compounding sizing:
# notional = capital * 2% * 10 = 0.2 * capital, fee = 0.13% of notional.
COMPOUND_FEE_RATE = 0.0013 * DEFAULT_SIZING_PCT / 100.0 * DEFAULT_LEVERAGE


def _interleaved_outcomes(wins: int, losses: int) -> list[bool]:
    """Alternate win/loss starting with a win, so results are reproducible."""
    out: list[bool] = []
    while wins or losses:
        if wins:
            out.append(True)
            wins -= 1
        if losses:
            out.append(False)
            losses -= 1
    return out


def compound_equity(
    capital: float,
    win_rate_pct: float,
    trades: int,
    win_mult: float = 1.04,
    loss_mult: float = 0.99,
    fee_rate: float = COMPOUND_FEE_RATE,
) -> float:
    """Final account equity when each trade is sized as a percent of current capital."""
    wins = round(win_rate_pct / 100.0 * trades)
    losses = trades - wins
    c = float(capital)
    for win in _interleaved_outcomes(wins, losses):
        c *= win_mult if win else loss_mult
        c -= fee_rate * c
    return c


def fixed_profit(preset_key: str, win_rate_pct: float, trades: int) -> float:
    """Profit with a constant margin, independent of account size."""
    preset = PRESETS[preset_key]
    p = win_rate_pct / 100.0
    return trades * (expected_value(p, preset.reward, preset.risk) - FIXED_FEE_PER_TRADE)


def percent_profit(preset_key: str, capital: float, win_rate_pct: float, trades: int) -> float:
    """Profit with margin = sizing% of initial capital. Non-compounding."""
    preset = PRESETS[preset_key]
    p = win_rate_pct / 100.0
    margin = capital * DEFAULT_SIZING_PCT / 100.0
    ratio = margin / BASE_MARGIN
    notional = margin * DEFAULT_LEVERAGE
    fee = futures_fee(notional)
    return trades * (expected_value(p, preset.reward * ratio, preset.risk * ratio) - fee)


def sweep_win_rates(
    preset_key: str, win_rate_pcts: list[float], capital: float, trades: int
) -> list[dict]:
    """Per win rate: net profit for the fixed, compounding, and RR-5.56 variants."""
    rows = []
    for wr in win_rate_pcts:
        p = wr / 100.0
        ev_a = expected_value(p, PRESETS["A"].reward, PRESETS["A"].risk)
        ev_c = expected_value(p, PRESETS["C"].reward, PRESETS["C"].risk)
        rows.append(
            {
                "wr": wr,
                "net_a": trades * (ev_a - FIXED_FEE_PER_TRADE),
                "net_b": compound_equity(capital, wr, trades) - capital,
                "net_c": trades * (ev_c - FIXED_FEE_PER_TRADE),
                "gross_a": trades * ev_a,
                "gross_c": trades * ev_c,
                "sh_a": sharpe_per_trade(p, PRESETS["A"].reward, PRESETS["A"].risk, FIXED_FEE_PER_TRADE),
                "sh_c": sharpe_per_trade(p, PRESETS["C"].reward, PRESETS["C"].risk, FIXED_FEE_PER_TRADE),
            }
        )
    return rows


def capital_scaling(
    preset_key: str, capitals: list[float], win_rate_pct: float, trades: int
) -> list[dict]:
    """Compare the three sizing models across account sizes."""
    rows = []
    for cap in capitals:
        rows.append(
            {
                "capital": cap,
                "fixed_value": fixed_profit(preset_key, win_rate_pct, trades),
                "percent_value": percent_profit(preset_key, cap, win_rate_pct, trades),
                "compounding_value": compound_equity(cap, win_rate_pct, trades) - cap,
            }
        )
    return rows


def best_by(rows: list[dict], key: str) -> dict:
    """Row with the highest value for key."""
    if not rows:
        raise ValueError("rows cannot be empty")
    return max(rows, key=lambda r: r[key])
