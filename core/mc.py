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

from core.fees import (
    FUTURES_FUNDING_PCT,
    FUTURES_TAKER_PCT,
    SPOT_FEE_FLOOR,
    SPOT_PCT,
    futures_fee,
    spot_fee,
)
from core.trading import sharpe_per_trade

DEFAULT_SEED = 12345


def _fee_rate(fee_model: str) -> float:
    """Fee per unit of notional, as a fraction.

    Used only by the analytic Kelly sizing guide. The spot model's per-trade
    floor is deliberately ignored here: it is a small-trade artefact, and Kelly
    is a sizing guide rather than a ledger.
    """
    if fee_model == "futures":
        return FUTURES_TAKER_PCT / 100.0 * 2 + FUTURES_FUNDING_PCT / 100.0
    if fee_model == "spot":
        return SPOT_PCT / 100.0 * 2
    raise ValueError("fee_model must be 'futures' or 'spot'")


def _fee_params(fee_model: str) -> tuple[float, float, float, float]:
    """``(num, den, floor, mult)``: the fee is ``max(notional*num/den, floor)*mult``.

    This is the exact decomposition of the models in ``core.fees``, written so
    the arithmetic stays bit-identical while the hot loop avoids a function call
    per simulated trade. A default run is ~900k trades, so those calls cost more
    than the simulation itself.

    The multiply-then-divide order is load-bearing: ``n * pct / 100`` and
    ``n * (pct / 100)`` differ by one ULP, so collapsing them would make the
    fast path quietly disagree with ``core.fees``.
    """
    if fee_model == "futures":
        # futures_fee: notional * (taker * 2 + funding), no floor, one side.
        return (FUTURES_TAKER_PCT / 100.0 * 2 + FUTURES_FUNDING_PCT / 100.0, 1.0, 0.0, 1.0)
    if fee_model == "spot":
        # spot_fee: max(notional * pct / 100, floor) * sides.
        return (SPOT_PCT, 100.0, SPOT_FEE_FLOOR, 2.0)
    raise ValueError("fee_model must be 'futures' or 'spot'")


def kelly_fraction(
    win_prob: float, rr: float, stop_pct: float, fee_model: str,
    slippage_pct: float = 0.0,
) -> float:
    """Full-Kelly fraction of equity to risk per trade, clamped to [0, 1].

    Kelly for a fixed-R bet is ``f* = p - q/rr`` when there is no friction.
    Fees and slippage change the win and loss outcomes asymmetrically, so the
    general two-outcome form is used instead. With ``s = stop_pct/100``, ``k``
    the fee per unit notional, and ``slip = slippage_pct/100``:

        a = rr - k/s             net win per unit risked
        d = 1 + (slip + k)/s     net loss per unit risked
        f* = (p*a - q*d) / (a*d)

    Returns 0.0 when the edge is not positive, so the caller never sees a
    negative or unbounded risk suggestion.
    """
    if not 0.0 <= win_prob <= 1.0:
        raise ValueError("win_prob must be within [0, 1]")
    if rr <= 0:
        raise ValueError("rr must be > 0")
    if stop_pct <= 0:
        raise ValueError("stop_pct must be > 0")
    if slippage_pct < 0:
        raise ValueError("slippage_pct must be >= 0")
    s = stop_pct / 100.0
    k = _fee_rate(fee_model)
    slip = slippage_pct / 100.0
    a = rr - k / s
    d = 1.0 + (slip + k) / s
    if a <= 0.0:
        # Fees alone consume the whole reward: there is no positive edge to size.
        return 0.0
    p = win_prob
    q = 1.0 - p
    f = (p * a - q * d) / (a * d)
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


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
    rr: float, leverage: float, fee_params: tuple[float, float, float, float],
    trades: int, win_prob: float, bust_level: float, slip_frac: float = 0.0,
) -> tuple[float, float]:
    """One Monte Carlo path.

    Returns ``(final_equity, max_drawdown_pct)``. Final equity is ``bust_level``
    if the path busted. Max drawdown is the deepest peak-to-trough fall in
    equity seen anywhere in the path, as a percentage of the running peak, so a
    path that doubles and then halves records a 50% drawdown.

    The position is sized from the *planned* stop. On a loss the exit slips by
    ``slip_frac``, so the realized loss is wider than planned: that is the
    real-world failure mode of sizing for a stop that does not fill.

    Everything that does not change per trade is hoisted above the loop, and the
    fee is computed inline from ``fee_params``, because a default run executes
    this body ~900k times and the per-trade function calls dominated the profile.
    """
    equity = float(capital)
    peak = equity
    max_dd = 0.0
    stop_frac = stop_pct / 100.0
    fee_num, fee_den, fee_floor, fee_mult = fee_params
    draw = rng.random
    for _ in range(trades):
        # Multiply-then-divide, matching the documented model exactly. Folding
        # risk_pct/100 into a single constant is one ULP off, which is enough to
        # make the simulation disagree with a naive reference implementation.
        risk_usd = equity * risk_pct / 100.0
        notional = risk_usd / stop_frac
        max_notional = equity * leverage
        if notional > max_notional:
            notional = max_notional
            risk_usd = notional * stop_frac
        fee = notional * fee_num / fee_den
        if fee < fee_floor:
            fee = fee_floor
        fee = fee * fee_mult
        if draw() < win_prob:
            equity += risk_usd * rr - fee
        else:
            equity -= risk_usd + notional * slip_frac + fee
        if equity > peak:
            peak = equity
        elif peak > 0.0:
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
    slippage_pct: float = 0.0,
) -> dict:
    """Run ``n_sims`` independent paths at one win rate.

    Returns mean/median final equity and net, the probability of success
    (ending above the starting capital) and of busting, plus the analytic
    per-trade expectancy and Sharpe at the starting capital.
    """
    _validate(capital, risk_pct, stop_pct, rr, leverage, trades, win_rate_pct, n_sims)
    if bust_pct < 0:
        raise ValueError("bust_pct must be >= 0")
    if slippage_pct < 0:
        raise ValueError("slippage_pct must be >= 0")

    win_prob = win_rate_pct / 100.0
    bust_level = capital * bust_pct / 100.0
    rng = random.Random(seed)
    slip_frac = slippage_pct / 100.0
    fee_params = _fee_params(fee_model)

    finals = []
    drawdowns = []
    for _ in range(n_sims):
        final, dd = _run_once(rng, capital, risk_pct, stop_pct, rr, leverage,
                              fee_params, trades, win_prob, bust_level, slip_frac)
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
        "kelly_pct": 100.0 * kelly_fraction(
            win_prob, rr, stop_pct, fee_model, slippage_pct
        ),
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
    slippage_pct: float = 0.0,
) -> list[dict]:
    """One Monte Carlo result per win rate.

    Each win rate gets its own derived seed, so rows are independent yet the
    whole table reproduces exactly for a given input.
    """
    if not win_rate_pcts:
        raise ValueError("win_rate_pcts cannot be empty")
    return [
        simulate(capital, risk_pct, stop_pct, rr, leverage, fee_model,
                 trades, wr, n_sims, bust_pct, seed + i, slippage_pct)
        for i, wr in enumerate(win_rate_pcts)
    ]


def summarise(rows: list[dict]) -> dict:
    """Headline figures for the result cards."""
    if not rows:
        raise ValueError("rows cannot be empty")
    best = max(rows, key=lambda r: r["mean_net"])
    worst_ruin = max(rows, key=lambda r: r["p_busted"])
    # Kelly is reported at the middle of the swept range, which is the row the
    # user is most likely to be looking at, and shown both full and halved:
    # full Kelly maximises growth but assumes the win rate is exactly right,
    # and it is brutally sensitive to that assumption being wrong.
    middle = rows[len(rows) // 2]
    return {
        "best_wr": best["wr"],
        "best_mean_net": best["mean_net"],
        "best_p_success": best["p_success"],
        "worst_ruin_wr": worst_ruin["wr"],
        "worst_ruin_p": worst_ruin["p_busted"],
        "kelly_pct": middle["kelly_pct"],
        "kelly_half_pct": middle["kelly_pct"] / 2.0,
        "kelly_wr": middle["wr"],
    }
