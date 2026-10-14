import pytest

from core.fees import (
    futures_fee,
    liquidation_distance_pct,
    liquidation_price,
    min_fee,
    percent_fee,
    spot_fee,
)


def test_futures_fee_on_20_notional():
    assert futures_fee(20.0) == pytest.approx(0.026)


def test_spot_fee_uses_floor_on_small_position():
    # spec 9.4: fomo round-trip on a $2 position
    assert spot_fee(2.0) == pytest.approx(1.90)


def test_spot_fee_is_percent_above_break_even():
    assert spot_fee(1000.0) == pytest.approx(10.0)


def test_spot_fee_at_break_even_notional():
    # 190 * 0.005 = 0.95 exactly, so the floor stops binding
    assert spot_fee(190.0) == pytest.approx(1.90)


def test_spot_fee_below_break_even_still_floored():
    assert spot_fee(189.0) == pytest.approx(1.90)


def test_percent_fee_sides():
    assert percent_fee(1000.0, 0.5, sides=1) == pytest.approx(5.0)
    assert percent_fee(1000.0, 0.5, sides=2) == pytest.approx(10.0)


def test_min_fee_helper():
    assert min_fee(2.0, 0.5, 0.95) == pytest.approx(1.90)


def test_liquidation_distance_at_10x():
    assert liquidation_price(100.0, 10) == pytest.approx(90.0)


def test_liquidation_short_is_mirrored():
    assert liquidation_price(100.0, 10, side="short") == pytest.approx(110.0)


def test_liquidation_distance_pct_at_10x():
    assert liquidation_distance_pct(10) == pytest.approx(-10.0)


def test_invalid_leverage_raises():
    with pytest.raises(ValueError):
        liquidation_price(100.0, 0.5)
    with pytest.raises(ValueError):
        liquidation_distance_pct(0)


def test_invalid_side_raises():
    with pytest.raises(ValueError):
        liquidation_price(100.0, 10, side="sideways")
