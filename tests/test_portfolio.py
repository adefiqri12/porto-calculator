import pytest

from core.portfolio import Holding, portfolio_future_value, validate_allocation


def test_valid_allocation_passes():
    validate_allocation([60.0, 30.0, 10.0])


def test_allocation_within_tolerance_passes():
    validate_allocation([60.0, 30.0, 10.005])


def test_allocation_summing_wrong_raises():
    with pytest.raises(ValueError):
        validate_allocation([60.0, 30.0, 20.0])


def test_negative_weight_raises():
    with pytest.raises(ValueError):
        validate_allocation([110.0, -10.0])


def test_empty_holdings_returns_zero():
    # Review Focus #3
    result = portfolio_future_value(1000, 12, [])
    assert result["total_fv"] == 0.0
    assert result["per_asset"] == []


def test_weights_split_the_monthly_contribution():
    holdings = [
        Holding(name="BBCA", weight_pct=50.0, annual_roi_pct=12.0),
        Holding(name="ETH", weight_pct=50.0, annual_roi_pct=24.0),
    ]
    result = portfolio_future_value(1_000_000, 12, holdings)
    assert result["per_asset"][0]["future_value"] < result["per_asset"][1]["future_value"]
    assert result["total_fv"] == pytest.approx(
        sum(a["future_value"] for a in result["per_asset"])
    )


def test_single_holding_equals_plain_dca():
    from core.dca import future_value

    holdings = [Holding(name="ALL", weight_pct=100.0, annual_roi_pct=12.0)]
    result = portfolio_future_value(1_000_000, 12, holdings)
    assert result["total_fv"] == pytest.approx(future_value(1_000_000, 12.0, 12))
