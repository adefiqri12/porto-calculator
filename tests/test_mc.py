"""Monte Carlo engine: reproducibility, risk behaviour, and edge cases."""
import pytest

from core.mc import DEFAULT_SEED, simulate, summarise, sweep

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
        {"wr": 20.0, "mean_net": -10.0, "p_success": 0.3, "p_busted": 0.6},
        {"wr": 50.0, "mean_net": 100.0, "p_success": 0.9, "p_busted": 0.01},
        {"wr": 60.0, "mean_net": 150.0, "p_success": 0.95, "p_busted": 0.0},
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


def test_default_seed_is_stable():
    assert DEFAULT_SEED == 12345
    assert simulate(win_rate_pct=50.0, **BASE) == simulate(win_rate_pct=50.0, **BASE)
