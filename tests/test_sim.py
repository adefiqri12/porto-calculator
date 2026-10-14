import pytest

from core.sim import (
    COMPOUND_FEE_RATE,
    FIXED_FEE_PER_TRADE,
    best_by,
    capital_scaling,
    compound_equity,
    sweep_win_rates,
)


def test_fixed_fee_matches_futures_fee_on_20_notional():
    assert FIXED_FEE_PER_TRADE == pytest.approx(0.026)


def test_compound_fee_rate():
    # 0.13% of a notional equal to 0.2 * capital -> 0.00026 * capital
    assert COMPOUND_FEE_RATE == pytest.approx(0.00026)


def test_compound_equity_matches_golden_b_net():
    # spec 9.1: netB @ WR50 = 319.08 (path ordering differs slightly; 0.5% tolerance)
    profit = compound_equity(100.0, 50.0, 100) - 100.0
    assert profit == pytest.approx(319.08, rel=0.005)


def test_compound_equity_gross_matches_golden_b():
    # spec 9.1: grossB @ WR50 = 329.96
    profit = compound_equity(100.0, 50.0, 100, fee_rate=0.0) - 100.0
    assert profit == pytest.approx(329.96, rel=0.005)


def test_compound_equity_is_deterministic():
    assert compound_equity(100.0, 50.0, 100) == compound_equity(100.0, 50.0, 100)


def test_sweep_rows_match_golden_table():
    rows = sweep_win_rates("A", [20.0, 50.0, 60.0], 100.0, 100)
    assert [r["wr"] for r in rows] == [20.0, 50.0, 60.0]
    assert rows[0]["net_a"] == pytest.approx(-2.60, abs=0.01)
    assert rows[1]["net_a"] == pytest.approx(147.40, abs=0.01)
    assert rows[1]["sh_a"] == pytest.approx(0.590, abs=1e-3)
    assert rows[2]["net_c"] == pytest.approx(525.40, abs=0.01)
    assert rows[0]["net_c"] == pytest.approx(53.40, abs=0.01)
    assert rows[1]["sh_c"] == pytest.approx(0.691, abs=1e-3)


def test_sweep_gross_matches_golden():
    rows = sweep_win_rates("A", [50.0], 100.0, 100)
    assert rows[0]["gross_a"] == pytest.approx(150.0)
    assert rows[0]["gross_c"] == pytest.approx(410.0)


def test_sweep_net_b_matches_golden_within_tolerance():
    rows = sweep_win_rates("A", [50.0], 100.0, 100)
    assert rows[0]["net_b"] == pytest.approx(319.08, rel=0.005)


def test_capital_scaling_fixed_is_constant_percent_scales():
    # spec 9.2: aFixed is capital-independent; aPct @ $500 = 737.00, @ $1000 = 1474.00
    rows = capital_scaling("A", [100.0, 500.0, 1000.0], 50.0, 100)
    assert rows[0]["fixed_value"] == pytest.approx(147.40, abs=0.01)
    assert rows[1]["fixed_value"] == pytest.approx(147.40, abs=0.01)
    assert rows[2]["fixed_value"] == pytest.approx(147.40, abs=0.01)
    assert rows[1]["percent_value"] == pytest.approx(737.00, rel=0.005)
    assert rows[2]["percent_value"] == pytest.approx(1474.00, rel=0.005)


def test_capital_scaling_strategy_c_percent():
    # spec 9.2: cPct @ $500 = 2037.00, @ $1000 = 4074.00
    rows = capital_scaling("C", [100.0, 500.0, 1000.0], 50.0, 100)
    assert rows[0]["fixed_value"] == pytest.approx(407.40, abs=0.01)
    assert rows[1]["percent_value"] == pytest.approx(2037.00, rel=0.005)
    assert rows[2]["percent_value"] == pytest.approx(4074.00, rel=0.005)


def test_capital_scaling_compounding_matches_golden_b():
    # spec 9.2: bPct @ $500 = 1595.38, @ $1000 = 3190.77
    rows = capital_scaling("B", [100.0, 500.0, 1000.0], 50.0, 100)
    assert rows[1]["compounding_value"] == pytest.approx(1595.38, rel=0.005)
    assert rows[2]["compounding_value"] == pytest.approx(3190.77, rel=0.005)


def test_best_by():
    rows = [{"k": 1.0}, {"k": 3.0}, {"k": 2.0}]
    assert best_by(rows, "k")["k"] == 3.0
    with pytest.raises(ValueError):
        best_by([], "k")
