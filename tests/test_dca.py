import pytest

from core.dca import future_value, yearly_breakdown


def test_future_value_matches_manual():
    # r = 0.01, n = 12 -> 1e6 * ((1.01**12 - 1)/0.01) * 1.01
    assert future_value(1_000_000, 12.0, 12) == pytest.approx(12_809_328.0433, rel=1e-6)


def test_zero_roi_returns_principal_only():
    # Review Focus #1: r == 0 must not divide by zero
    assert future_value(1000, 0.0, 12) == pytest.approx(12_000.0)


def test_zero_months_returns_zero():
    # Review Focus #5
    assert future_value(1000, 12.0, 0) == pytest.approx(0.0)


def test_negative_months_returns_zero():
    assert future_value(1000, 12.0, -3) == pytest.approx(0.0)


def test_yearly_breakdown_length_and_totals():
    rows = yearly_breakdown(1_000_000, 12.0, 24)
    assert len(rows) == 2
    assert rows[-1]["contributed"] == pytest.approx(24_000_000)
    assert rows[-1]["value"] == pytest.approx(future_value(1_000_000, 12.0, 24))
    assert rows[-1]["return"] == pytest.approx(rows[-1]["value"] - rows[-1]["contributed"])


def test_yearly_breakdown_zero_months_is_empty():
    # Review Focus #5
    assert yearly_breakdown(1000, 12.0, 0) == []


def test_yearly_breakdown_partial_year_is_omitted():
    assert len(yearly_breakdown(1000, 12.0, 11)) == 0
