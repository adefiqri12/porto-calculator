import pytest

from core.rates import annual_to_monthly, cagr


def test_cagr_matches_manual_computation():
    # (1 + 1.50) ** (1/5) - 1 = 0.2011244...  -> 20.11244 %
    assert cagr(150.0, 5) == pytest.approx(20.11244, rel=1e-5)


def test_cagr_single_year_is_identity():
    assert cagr(20.0, 1) == pytest.approx(20.0)


def test_cagr_zero_return():
    assert cagr(0.0, 10) == pytest.approx(0.0)


def test_cagr_zero_years_raises():
    with pytest.raises(ValueError):
        cagr(20.0, 0)


def test_annual_to_monthly():
    assert annual_to_monthly(12.0) == pytest.approx(0.01)
