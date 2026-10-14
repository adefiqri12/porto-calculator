"""Monte Carlo engine: reproducibility, risk behaviour, and edge cases."""
import pytest

from core.mc import DEFAULT_SEED, kelly_fraction, simulate, summarise, sweep

BASE = dict(capital=100.0, risk_pct=1.0, stop_pct=5.0, rr=4.0,
            leverage=10.0, fee_model="futures", trades=100, n_sims=500)


def test_same_seed_reproduces_exactly():
    a = simulate(win_rate_pct=50.0, **BASE)
    b = simulate(win_rate_pct=50.0, **BASE)
    assert a == b


def test_different_seed_changes_result():
    a = simulate(win_rate_pct=50.0, seed=1, **BASE)
    b = simulate(win_rate_pct=50.0, seed=2, **BASE)
    assert a["mean_net"] != b["mean_net"]


def test_probabilities_are_fractions_and_do_not_overlap():
    r = simulate(win_rate_pct=30.0, **BASE)
    assert 0.0 <= r["p_success"] <= 1.0
    assert 0.0 <= r["p_busted"] <= 1.0
    # A path cannot both end above start and have busted.
    assert r["p_success"] + r["p_busted"] <= 1.0 + 1e-12


def test_higher_win_rate_raises_success_probability():
    lo = simulate(win_rate_pct=20.0, **BASE)
    hi = simulate(win_rate_pct=70.0, **BASE)
    assert hi["p_success"] > lo["p_success"]
    assert hi["mean_net"] > lo["mean_net"]


def test_extreme_risk_busts_and_conservative_risk_does_not():
    # Break-even WR for 4:1 is 20%, so 15% is a genuinely losing edge.
    safe = simulate(win_rate_pct=15.0, risk_pct=0.5, n_sims=300, capital=100.0,
                    stop_pct=5.0, rr=4.0, leverage=10.0, fee_model="futures", trades=50)
    reckless = simulate(win_rate_pct=15.0, risk_pct=50.0, n_sims=300, capital=100.0,
                        stop_pct=5.0, rr=4.0, leverage=10.0, fee_model="futures", trades=50)
    assert safe["p_busted"] == 0.0
    assert reckless["p_busted"] > 0.9


def test_equity_never_falls_below_bust_level():
    # bust_pct 10 -> a busted path is floored at 10, never negative.
    r = simulate(win_rate_pct=10.0, risk_pct=40.0, n_sims=200, capital=100.0,
                 stop_pct=5.0, rr=1.0, leverage=10.0, fee_model="futures",
                 trades=100, bust_pct=10.0)
    assert r["mean_final"] >= 10.0


def test_breakeven_win_rate_gives_zero_expectancy():
    # Break-even WR for RR 4:1 is 1/5 = 20%. At exactly 20% the analytic
    # expectancy should be ~0 minus the fee.
    r = simulate(win_rate_pct=20.0, **BASE)
    assert r["expectancy"] == pytest.approx(-r["fee_per_trade"], abs=1e-9)


def test_sharpe_matches_golden_at_4to1_50pct():
    # rr 4, risk 1 -> reward 4, matching report strategy A's 0.590.
    r = simulate(win_rate_pct=50.0, **BASE)
    assert r["sharpe"] == pytest.approx(0.590, abs=1e-3)


def test_notional_respects_leverage_cap():
    # risk 1% of 100 = $1, stop 5% -> notional 20. Cap = 100 * 10 = 1000.
    r = simulate(win_rate_pct=50.0, **BASE)
    assert r["notional"] == pytest.approx(20.0)


def test_leverage_cap_binds_when_stop_is_tight():
    # risk 1% ($1), stop 0.05% -> notional would be 2000, but cap is 1000.
    r = simulate(win_rate_pct=50.0, capital=100.0, risk_pct=1.0, stop_pct=0.05,
                 rr=4.0, leverage=10.0, fee_model="futures", trades=10, n_sims=10)
    assert r["notional"] == pytest.approx(1000.0)


def test_spot_fees_differ_from_futures():
    fut = simulate(win_rate_pct=50.0, **BASE)
    spot = simulate(win_rate_pct=50.0, **{**BASE, "fee_model": "spot"})
    assert spot["fee_per_trade"] != fut["fee_per_trade"]
    assert spot["mean_net"] < fut["mean_net"]


def test_sweep_returns_one_row_per_win_rate():
    rows = sweep(capital=100.0, risk_pct=1.0, stop_pct=5.0, rr=4.0, leverage=10.0,
                 fee_model="futures", trades=100, win_rate_pcts=[20.0, 40.0, 60.0],
                 n_sims=100)
    assert [r["wr"] for r in rows] == [20.0, 40.0, 60.0]
    assert all(0.0 <= r["p_success"] <= 1.0 for r in rows)


def test_sweep_rows_are_independent_but_reproducible():
    args = dict(capital=100.0, risk_pct=1.0, stop_pct=5.0, rr=4.0, leverage=10.0,
                fee_model="futures", trades=100, win_rate_pcts=[20.0, 50.0], n_sims=200)
    first = sweep(**args)
    second = sweep(**args)
    assert first == second
    # Adjacent win rates must not share a result (they would with one shared seed).
    assert first[0]["mean_net"] != first[1]["mean_net"]


def test_summarise_picks_best_net_and_worst_ruin():
    rows = [
        {"wr": 20.0, "mean_net": -10.0, "p_success": 0.3, "p_busted": 0.6,
         "kelly_pct": 0.0},
        {"wr": 50.0, "mean_net": 100.0, "p_success": 0.9, "p_busted": 0.01,
         "kelly_pct": 40.0},
        {"wr": 60.0, "mean_net": 150.0, "p_success": 0.95, "p_busted": 0.0,
         "kelly_pct": 55.0},
    ]
    s = summarise(rows)
    assert s["best_wr"] == 60.0
    assert s["best_mean_net"] == 150.0
    assert s["worst_ruin_wr"] == 20.0
    assert s["worst_ruin_p"] == 0.6


@pytest.mark.parametrize("bad", [
    {"capital": 0.0}, {"capital": -1.0}, {"risk_pct": -1.0}, {"stop_pct": 0.0},
    {"rr": 0.0}, {"leverage": 0.5}, {"trades": 0}, {"win_rate_pct": 101.0},
    {"win_rate_pct": -1.0}, {"n_sims": 0}, {"bust_pct": -1.0},
])
def test_invalid_inputs_raise(bad):
    args = {**BASE, "win_rate_pct": 50.0, **bad}
    with pytest.raises(ValueError):
        simulate(**args)


def test_unknown_fee_model_raises():
    with pytest.raises(ValueError):
        simulate(win_rate_pct=50.0, **{**BASE, "fee_model": "nonsense"})


def test_zero_risk_never_busts():
    r = simulate(win_rate_pct=30.0, risk_pct=0.0, n_sims=200, capital=100.0,
                 stop_pct=5.0, rr=4.0, leverage=10.0, fee_model="futures", trades=50)
    assert r["p_busted"] == 0.0


def test_position_sizing_scales_risk_with_the_stop():
    # Wider stop -> smaller position for the same dollar risk.
    tight = simulate(win_rate_pct=50.0, **{**BASE, "stop_pct": 2.0})
    wide = simulate(win_rate_pct=50.0, **{**BASE, "stop_pct": 10.0})
    assert tight["notional"] > wide["notional"]
    # Dollar risk is held at 1% of capital either way.
    assert tight["notional"] * 0.02 == pytest.approx(1.0)
    assert wide["notional"] * 0.10 == pytest.approx(1.0)


def test_reward_risk_moves_break_even_win_rate():
    # At the break-even WR, expectancy is exactly the fee (i.e. ~0 before it).
    for rr in (1.0, 2.0, 4.0, 9.0):
        be_wr = 100.0 / (1.0 + rr)
        r = simulate(win_rate_pct=be_wr, **{**BASE, "rr": rr})
        assert r["expectancy"] == pytest.approx(-r["fee_per_trade"], abs=1e-9)


def test_drawdown_is_reported_and_bounded():
    r = simulate(win_rate_pct=50.0, **BASE)
    assert 0.0 <= r["mean_max_dd"] <= 100.0
    assert 0.0 <= r["worst_max_dd"] <= 100.0
    # The worst path can never be shallower than the average.
    assert r["worst_max_dd"] >= r["mean_max_dd"]


def test_drawdown_grows_with_risk():
    low = simulate(win_rate_pct=50.0, **{**BASE, "risk_pct": 1.0})
    high = simulate(win_rate_pct=50.0, **{**BASE, "risk_pct": 20.0})
    assert high["mean_max_dd"] > low["mean_max_dd"]


def test_drawdown_shrinks_with_a_better_edge():
    bad = simulate(win_rate_pct=20.0, **BASE)
    good = simulate(win_rate_pct=60.0, **BASE)
    assert good["mean_max_dd"] < bad["mean_max_dd"]


def test_winning_path_with_no_losses_has_zero_drawdown():
    # 100% win rate: equity only ever rises, so drawdown is exactly 0.
    r = simulate(win_rate_pct=100.0, **BASE)
    assert r["mean_max_dd"] == pytest.approx(0.0, abs=1e-9)
    assert r["worst_max_dd"] == pytest.approx(0.0, abs=1e-9)


def test_extreme_leverage_cannot_report_over_100pct_drawdown():
    # risk_pct=100 makes risk_usd equal the whole equity, and stop_pct=50 keeps
    # the leverage cap from binding, so a single loss drives equity below zero
    # purely through the fee. Raw drawdown would then exceed 100%; the reported
    # figure must be clamped to exactly 100.0, not just "under 100".
    r = simulate(win_rate_pct=50.0, **{**BASE, "capital": 1000.0, "risk_pct": 100.0,
                                       "stop_pct": 50.0, "leverage": 10.0,
                                       "trades": 5, "n_sims": 500})
    assert r["worst_max_dd"] == pytest.approx(100.0)
    assert 0.0 <= r["mean_max_dd"] <= 100.0


def test_default_seed_is_stable():
    assert DEFAULT_SEED == 12345
    assert simulate(win_rate_pct=50.0, **BASE) == simulate(win_rate_pct=50.0, **BASE)


def test_slippage_zero_matches_omitted_argument():
    # slippage_pct=0.0 must be a true no-op: the default path is untouched.
    with_zero = simulate(win_rate_pct=50.0, slippage_pct=0.0, **BASE)
    omitted = simulate(win_rate_pct=50.0, **BASE)
    assert with_zero == omitted


def test_higher_slippage_lowers_mean_net():
    clean = simulate(win_rate_pct=50.0, **BASE)
    slipped = simulate(win_rate_pct=50.0, **{**BASE, "slippage_pct": 2.0})
    assert slipped["mean_net"] < clean["mean_net"]


def test_higher_slippage_never_lowers_p_busted():
    # 5% risk with a losing edge busts a good fraction of paths but not all of
    # them, so the wider realized loss has room to raise the ruin rate.
    args = dict(capital=100.0, risk_pct=5.0, stop_pct=5.0, rr=4.0,
                leverage=10.0, fee_model="futures", trades=100, n_sims=500)
    clean = simulate(win_rate_pct=15.0, **args)
    slipped = simulate(win_rate_pct=15.0, slippage_pct=3.0, **args)
    assert slipped["p_busted"] >= clean["p_busted"]
    # Non-vacuous: the wider realized loss must actually change the outcome.
    assert slipped["p_busted"] > clean["p_busted"]


def test_slippage_does_not_touch_a_win_only_path():
    # With no losing trades there is nothing to slip on, so mean_final is
    # identical with and without slippage. Exact equality, not approx.
    clean = simulate(win_rate_pct=100.0, **BASE)
    slipped = simulate(win_rate_pct=100.0, **{**BASE, "slippage_pct": 5.0})
    assert slipped["mean_final"] == clean["mean_final"]


def test_negative_slippage_raises():
    with pytest.raises(ValueError):
        simulate(win_rate_pct=50.0, slippage_pct=-1.0, **BASE)


def test_kelly_approaches_frictionless_with_a_wide_stop():
    # With stop_pct=50 the fee term k/s is tiny (0.0013/0.5 ~ 0.0026), so the
    # fee-aware fraction is close to the frictionless p - q/rr.
    p = 0.5
    rr = 4.0
    frictionless = p - (1.0 - p) / rr
    got = kelly_fraction(p, rr, stop_pct=50.0, fee_model="futures")
    assert got == pytest.approx(frictionless, abs=0.01)


def test_kelly_positive_edge_is_positive_and_tiny_edge_is_clamped_to_zero():
    assert kelly_fraction(0.5, 4.0, stop_pct=5.0, fee_model="futures") > 0.0
    # p=0.01 at 4:1 is deeply negative edge; it must clamp to exactly 0.0.
    assert kelly_fraction(0.01, 4.0, stop_pct=5.0, fee_model="futures") == 0.0


def test_kelly_increases_with_win_prob():
    lo = kelly_fraction(0.4, 4.0, stop_pct=5.0, fee_model="futures")
    hi = kelly_fraction(0.6, 4.0, stop_pct=5.0, fee_model="futures")
    assert hi > lo


def test_fees_and_slippage_reduce_kelly():
    clean = kelly_fraction(0.5, 4.0, stop_pct=5.0, fee_model="futures")
    with_slip = kelly_fraction(0.5, 4.0, stop_pct=5.0, fee_model="futures",
                               slippage_pct=2.0)
    # Zero fees are not a supported model, so compare futures against a much
    # higher fee via spot, which charges far more per unit notional.
    high_fee = kelly_fraction(0.5, 4.0, stop_pct=5.0, fee_model="spot")
    assert with_slip < clean
    assert high_fee < clean


def test_kelly_is_always_within_unit_interval():
    # The [0, 1] bound is guaranteed by construction (clamped), so pair it with
    # a discriminating assertion that a strong edge is strictly inside (0, 1).
    strong = kelly_fraction(0.9, 4.0, stop_pct=5.0, fee_model="futures")
    assert 0.0 <= strong <= 1.0
    assert 0.0 < strong < 1.0
    for p in (0.0, 0.01, 0.5, 0.99, 1.0):
        f = kelly_fraction(p, 4.0, stop_pct=5.0, fee_model="futures")
        assert 0.0 <= f <= 1.0


def test_simulate_kelly_pct_wires_the_fraction_through():
    r = simulate(win_rate_pct=50.0, **BASE)
    expected = 100.0 * kelly_fraction(0.5, BASE["rr"], BASE["stop_pct"],
                                      BASE["fee_model"])
    assert r["kelly_pct"] == pytest.approx(expected)


def test_summarise_kelly_fields_are_consistent():
    rows = sweep(capital=100.0, risk_pct=1.0, stop_pct=5.0, rr=4.0, leverage=10.0,
                 fee_model="futures", trades=100, win_rate_pcts=[20.0, 50.0, 80.0],
                 n_sims=100)
    s = summarise(rows)
    assert s["kelly_pct"] == pytest.approx(s["kelly_half_pct"] * 2.0)
    # kelly_wr is the win rate of the row at the median win rate.
    assert s["kelly_wr"] in [r["wr"] for r in rows]
    assert s["kelly_wr"] == 50.0


# --- The fast fee path in _run_once must agree exactly with core.fees. ---
# _run_once inlines the fee to avoid a function call per simulated trade, which
# made a default run roughly 1.5x faster. The decomposition is written to be
# bit-identical, including the multiply-then-divide order that core.fees uses,
# so these tests fail loudly if someone "simplifies" it back into disagreement.

def test_fee_params_match_core_fees_bit_for_bit():
    import random as _random

    from core.fees import futures_fee, spot_fee
    from core.mc import _fee_params

    rng = _random.Random(20261014)
    for model, reference in (("futures", futures_fee), ("spot", spot_fee)):
        num, den, floor, mult = _fee_params(model)
        for _ in range(20000):
            notional = rng.uniform(0.0, 1_000_000.0)
            fee = notional * num / den
            if fee < floor:
                fee = floor
            fee = fee * mult
            # Exact equality, not approx: a one-ULP drift here means the
            # simulation is silently charging a different fee than core.fees.
            assert fee == reference(notional), (model, notional, fee, reference(notional))


def test_simulate_matches_a_naive_reference_implementation():
    """Lock the optimised loop to the documented position model.

    This re-implements the per-trade arithmetic the slow, obvious way (fee via
    core.fees, no hoisting) and asserts the two agree exactly, so the
    optimisation cannot drift away from the model it claims to implement.
    """
    import random as _random

    from core.fees import futures_fee
    from core.mc import _run_once, _fee_params

    capital, risk_pct, stop_pct, rr, leverage = 1000.0, 2.0, 4.0, 3.0, 10.0
    trades, win_prob, bust_level, slip = 60, 0.45, 100.0, 0.0

    def naive(rng):
        equity = float(capital)
        peak = equity
        max_dd = 0.0
        for _ in range(trades):
            risk_usd = equity * risk_pct / 100.0
            notional = risk_usd / (stop_pct / 100.0)
            if notional > equity * leverage:
                notional = equity * leverage
                risk_usd = notional * (stop_pct / 100.0)
            fee = futures_fee(notional)
            if rng.random() < win_prob:
                equity += risk_usd * rr - fee
            else:
                equity -= risk_usd + fee
            peak = max(peak, equity)
            if peak > 0.0:
                max_dd = max(max_dd, min((peak - equity) / peak * 100.0, 100.0))
            if equity <= bust_level:
                return bust_level, max_dd
        return equity, max_dd

    params = _fee_params("futures")
    for seed in (1, 2, 3, 99, 12345):
        want = naive(_random.Random(seed))
        got = _run_once(_random.Random(seed), capital, risk_pct, stop_pct, rr,
                        leverage, params, trades, win_prob, bust_level, slip)
        assert got == want, seed
