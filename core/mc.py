"""Monte Carlo simulation of a manually specified trading strategy.

No presets. The caller supplies risk per trade, stop distance, reward:risk,
leverage, and fee model, and the engine resamples win/loss order many times.

Position model (per trade, compounding on current equity):

    risk_usd  = equity * risk_pct / 100        # loss if the stop is hit
    notional  = risk_usd / (stop_pct / 100)    # position size implied by the stop
    notional  = min(notional, equity * leverage)   # leverage caps exposure
    risk_usd  = notional * (stop_pct / 100)    # risk shrinks if leverage capped it
    fee       = fee_model(notional)
    win  -> equity += risk_usd * rr - fee
    lose -> equity -= risk_usd + fee

A run is "busted" once equity falls to or below ``bust_pct`` percent of the
starting capital, and stops there. A run is a "success" if it ends above the
starting capital. Everything is seeded, so a given input always reproduces the
same numbers: Monte Carlo without a seed is not testable.
"""
import math
import random
import statistics

from core.fees import futures_fee, spot_fee
from core.trading import sharpe_per_trade

DEFAULT_SEED = 12345


def _fee(notional: float, fee_model: str) -> float:
    if fee_model == "futures":
        return futures_fee(notional)
    if fee_model == "spot":
        return spot_fee(notional)
    raise ValueError("fee_model must be 'futures' or 'spot'")


def _validate(
    capital: float, risk_pct: float, stop_pct: float, rr: float,
    leverage: float, trades: int, win_rate_pct: float, n_sims: int,
) -> None:
    if capital <= 0:
        raise ValueError("capital must be > 0")
    if risk_pct < 0:
        raise ValueError("risk_pct must be >= 0")
    if stop_pct <= 0:
        raise ValueError("stop_pct must be > 0")
    if rr <= 0:
        raise ValueError("rr must be > 0")
    if leverage < 1:
        raise ValueError("leverage must be >= 1")
    if trades < 1:
        raise ValueError("trades must be >= 1")
    if not 0.0 <= win_rate_pct <= 100.0:
        raise ValueError("win_rate_pct must be within [0, 100]")
    if n_sims < 1:
        raise ValueError("n_sims must be >= 1")


def _run_once(
    rng: random.Random, capital: float, risk_pct: float, stop_pct: float,
    rr: float, leverage: float, fee_model: str, trades: int,
    win_prob: float, bust_level: float,
) -> tuple[float, float]:
    """One Monte Carlo path.

    Returns ``(final_equity, max_drawdown_pct)``. Final equity is ``bust_level``
    if the path busted. Max drawdown is the deepest peak-to-trough fall in
    equity seen anywhere in the path, as a percentage of the running peak, so a
    path that doubles and then halves records a 50% drawdown.
    """
    equity = float(capital)
    peak = equity
    max_dd = 0.0
    stop_frac = stop_pct / 100.0
    for _ in range(trades):
        risk_usd = equity * risk_pct / 100.0
        notional = risk_usd / stop_frac
        max_notional = equity * leverage
        if notional > max_notional:
            notional = max_notional
            risk_usd = notional * stop_frac
        fee = _fee(notional, fee_model)
        if rng.random() < win_prob:
            equity += risk_usd * rr - fee
        else:
            equity -= risk_usd + fee
        if equity > peak:
            peak = equity
        if peak > 0.0:
            dd = (peak - equity) / peak * 100.0
            # A drawdown cannot meaningfully exceed 100% of the peak: once you
            # have lost the whole peak there is nothing left to lose. Extreme
            # leverage can drive equity negative within a single trade, so clamp.
            if dd > 100.0:
                dd = 100.0
            if dd > max_dd:
                max_dd = dd
        if equity <= bust_level:
            return bust_level, max_dd
    return equity, max_dd


def simulate(
    capital: float,
    risk_pct: float,
    stop_pct: float,
    rr: float,
    leverage: float,
    fee_model: str,
    trades: int,
    win_rate_pct: float,
    n_sims: int,
    bust_pct: float = 10.0,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Run ``n_sims`` independent paths at one win rate.

    Returns mean/median final equity and net, the probability of success
    (ending above the starting capital) and of busting, plus the analytic
    per-trade expectancy and Sharpe at the starting capital.
    """
    _validate(capital, risk_pct, stop_pct, rr, leverage, trades, win_rate_pct, n_sims)
    if bust_pct < 0:
        raise ValueError("bust_pct must be >= 0")

    win_prob = win_rate_pct / 100.0
    bust_level = capital * bust_pct / 100.0
    rng = random.Random(seed)

    finals = []
    drawdowns = []
    for _ in range(n_sims):
        final, dd = _run_once(rng, capital, risk_pct, stop_pct, rr, leverage,
                              fee_model, trades, win_prob, bust_level)
        finals.append(final)
        drawdowns.append(dd)

    nets = [f - capital for f in finals]
    busted = sum(1 for f in finals if f <= bust_level + 1e-12)
    succeeded = sum(1 for f in finals if f > capital)

    # Expectancy and Sharpe at the starting capital, so they stay comparable
    # across win rates (the Monte Carlo mean already includes compounding).
    risk_usd = capital * risk_pct / 100.0
    notional = min(risk_usd / (stop_pct / 100.0), capital * leverage)
    risk_usd = notional * (stop_pct / 100.0)
    fee = _fee(notional, fee_model)
    reward_usd = risk_usd * rr

    return {
        "wr": win_rate_pct,
        "mean_final": statistics.fmean(finals),
        "median_final": statistics.median(finals),
        "mean_net": statistics.fmean(nets),
        "median_net": statistics.median(nets),
        "p_success": succeeded / n_sims,
        "p_busted": busted / n_sims,
        "mean_max_dd": statistics.fmean(drawdowns),
        "worst_max_dd": max(drawdowns),
        "expectancy": win_prob * reward_usd - (1.0 - win_prob) * risk_usd - fee,
        "sharpe": sharpe_per_trade(win_prob, reward_usd, risk_usd, fee),
        "notional": notional,
        "fee_per_trade": fee,
        "n_sims": n_sims,
    }


def sweep(
    capital: float,
    risk_pct: float,
    stop_pct: float,
    rr: float,
    leverage: float,
    fee_model: str,
    trades: int,
    win_rate_pcts: list[float],
    n_sims: int,
    bust_pct: float = 10.0,
    seed: int = DEFAULT_SEED,
) -> list[dict]:
    """One Monte Carlo result per win rate.

    Each win rate gets its own derived seed, so rows are independent yet the
    whole table reproduces exactly for a given input.
    """
    if not win_rate_pcts:
        raise ValueError("win_rate_pcts cannot be empty")
    return [
        simulate(capital, risk_pct, stop_pct, rr, leverage, fee_model,
                 trades, wr, n_sims, bust_pct, seed + i)
        for i, wr in enumerate(win_rate_pcts)
    ]


def summarise(rows: list[dict]) -> dict:
    """Headline figures for the result cards."""
    if not rows:
        raise ValueError("rows cannot be empty")
    best = max(rows, key=lambda r: r["mean_net"])
    worst_ruin = max(rows, key=lambda r: r["p_busted"])
    return {
        "best_wr": best["wr"],
        "best_mean_net": best["mean_net"],
        "best_p_success": best["p_success"],
        "worst_ruin_wr": worst_ruin["wr"],
        "worst_ruin_p": worst_ruin["p_busted"],
    }
