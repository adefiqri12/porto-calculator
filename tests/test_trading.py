import pytest

from core.trading import (
    break_even_win_rate,
    expected_value,
    gross_profit,
    net_profit,
    profit_factor,
    sharpe_per_trade,
    std_per_trade,
)


def test_expected_value_strategy_a():
    # 0.5*4 - 0.5*1 = 1.5
    assert expected_value(0.5, 4.0, 1.0) == pytest.approx(1.5)


def test_break_even_win_rate_for_rr_4():
    assert break_even_win_rate(4.0, 1.0) == pytest.approx(0.2)


def test_profit_factor_at_50pct():
    assert profit_factor(0.5, 4.0, 1.0) == pytest.approx(4.0)


def test_std_per_trade_strategy_a():
    assert std_per_trade(0.5, 4.0, 1.0) == pytest.approx(2.5)


def test_sharpe_matches_golden_strategy_a():
    # spec 9.1: shA @ WR50 = 0.590
    assert sharpe_per_trade(0.5, 4.0, 1.0, fee=0.026) == pytest.approx(0.590, abs=1e-3)


def test_sharpe_matches_golden_strategy_c():
    # spec 9.1: shC @ WR50 = 0.691
    assert sharpe_per_trade(0.5, 10.0, 1.8, fee=0.026) == pytest.approx(0.691, abs=1e-3)


def test_sharpe_golden_at_wr_20_and_60():
    # spec 9.1: shA @20 = -0.013, shA @60 = 0.806, shC @20 = 0.113, shC @60 = 0.909
    assert sharpe_per_trade(0.2, 4.0, 1.0, fee=0.026) == pytest.approx(-0.013, abs=1e-3)
    assert sharpe_per_trade(0.6, 4.0, 1.0, fee=0.026) == pytest.approx(0.806, abs=1e-3)
    assert sharpe_per_trade(0.2, 10.0, 1.8, fee=0.026) == pytest.approx(0.113, abs=1e-3)
    assert sharpe_per_trade(0.6, 10.0, 1.8, fee=0.026) == pytest.approx(0.909, abs=1e-3)


def test_net_profit_golden_a_and_c():
    assert net_profit(0.5, 4.0, 1.0, 0.026, 100) == pytest.approx(147.40, abs=0.01)
    assert net_profit(0.5, 10.0, 1.8, 0.026, 100) == pytest.approx(407.40, abs=0.01)
    assert net_profit(0.2, 4.0, 1.0, 0.026, 100) == pytest.approx(-2.60, abs=0.01)
    assert net_profit(0.2, 10.0, 1.8, 0.026, 100) == pytest.approx(53.40, abs=0.01)
    assert net_profit(0.6, 4.0, 1.0, 0.026, 100) == pytest.approx(197.40, abs=0.01)
    assert net_profit(0.6, 10.0, 1.8, 0.026, 100) == pytest.approx(525.40, abs=0.01)


def test_gross_profit_golden_a():
    assert gross_profit(0.5, 4.0, 1.0, 100) == pytest.approx(150.0)


def test_zero_or_hundred_win_rate_sharpe_is_zero():
    # Review Focus #2: std == 0 must not divide by zero
    assert sharpe_per_trade(0.0, 4.0, 1.0, fee=0.026) == 0.0
    assert sharpe_per_trade(1.0, 4.0, 1.0, fee=0.026) == 0.0


def test_zero_reward_and_risk_raises():
    # Review Focus #4
    with pytest.raises(ValueError):
        break_even_win_rate(0.0, 0.0)
    with pytest.raises(ValueError):
        profit_factor(0.5, 0.0, 0.0)
