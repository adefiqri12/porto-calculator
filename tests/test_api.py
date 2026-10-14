import pytest
from fastapi.testclient import TestClient

from api.app import create_app

client = TestClient(create_app())


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_presets_has_four_strategies():
    body = client.get("/api/presets").json()
    assert set(body) == {"A", "B", "C", "fomo"}
    assert body["A"]["rr"] == pytest.approx(4.0)


def test_cagr_endpoint():
    r = client.post("/api/cagr", json={"total_return_pct": 150.0, "years": 5})
    assert r.status_code == 200
    assert r.json()["cagr_pct"] == pytest.approx(20.11244, rel=1e-5)


def test_dca_endpoint():
    r = client.post("/api/dca", json={"monthly": 1_000_000, "annual_roi_pct": 12.0, "months": 12})
    assert r.status_code == 200
    body = r.json()
    assert body["future_value"] == pytest.approx(12_809_328.0433, rel=1e-6)
    assert body["total_invested"] == pytest.approx(12_000_000)
    assert len(body["yearly"]) == 1
    assert "return" in body["yearly"][0]


def test_portfolio_endpoint():
    r = client.post("/api/portfolio", json={
        "monthly": 1_000_000, "months": 12,
        "holdings": [
            {"name": "BBCA", "weight_pct": 50.0, "annual_roi_pct": 12.0},
            {"name": "ETH", "weight_pct": 50.0, "annual_roi_pct": 24.0},
        ]})
    assert r.status_code == 200
    assert r.json()["total_fv"] > 0


def test_portfolio_rejects_bad_weights():
    r = client.post("/api/portfolio", json={
        "monthly": 1_000_000, "months": 12,
        "holdings": [{"name": "X", "weight_pct": 90.0, "annual_roi_pct": 12.0}]})
    assert r.status_code == 422


def test_trading_endpoint_matches_golden():
    r = client.post("/api/trading", json={
        "win_rate_pct": 50.0, "reward": 4.0, "risk": 1.0,
        "leverage": 10.0, "fee_model": "futures", "capital": 100.0, "trades": 100})
    assert r.status_code == 200
    body = r.json()
    assert body["net_profit"] == pytest.approx(147.40, abs=0.01)
    assert body["sharpe"] == pytest.approx(0.590, abs=1e-3)
    assert body["break_even_win_rate_pct"] == pytest.approx(20.0)
    assert body["fee_per_trade"] == pytest.approx(0.026)


def test_trading_liquidation_warning_for_strategy_c():
    # stop at 9% price move vs 10% liquidation distance -> warning
    r = client.post("/api/trading", json={
        "win_rate_pct": 50.0, "reward": 10.0, "risk": 1.8,
        "leverage": 10.0, "fee_model": "futures", "capital": 100.0, "trades": 100})
    assert r.json()["liquidation_warning"] is True


def test_trading_no_warning_for_strategy_a():
    r = client.post("/api/trading", json={
        "win_rate_pct": 50.0, "reward": 4.0, "risk": 1.0,
        "leverage": 10.0, "fee_model": "futures", "capital": 100.0, "trades": 100})
    assert r.json()["liquidation_warning"] is False


def test_simulate_endpoint():
    r = client.post("/api/simulate", json={"preset": "A", "capital": 100.0, "trades": 100})
    assert r.status_code == 200
    body = r.json()
    row50 = next(x for x in body["rows"] if x["wr"] == 50.0)
    assert row50["net_a"] == pytest.approx(147.40, abs=0.01)
    assert body["best_by_sharpe"]["strategy"] in {"A", "C"}
    assert body["best_by_net"]["strategy"] in {"A", "B", "C"}


def test_simulate_rejects_unknown_preset():
    r = client.post("/api/simulate", json={"preset": "Z"})
    assert r.status_code == 422


def test_invalid_months_rejected():
    r = client.post("/api/dca", json={"monthly": 1000, "annual_roi_pct": 12.0, "months": 0})
    assert r.status_code == 422


def test_invalid_win_rate_rejected():
    r = client.post("/api/trading", json={
        "win_rate_pct": 150.0, "reward": 4.0, "risk": 1.0,
        "leverage": 10.0, "fee_model": "futures", "capital": 100.0, "trades": 100})
    assert r.status_code == 422


def test_invalid_leverage_rejected():
    r = client.post("/api/trading", json={
        "win_rate_pct": 50.0, "reward": 4.0, "risk": 1.0,
        "leverage": 0.5, "fee_model": "futures", "capital": 100.0, "trades": 100})
    assert r.status_code == 422
