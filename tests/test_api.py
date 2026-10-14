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
    r = client.post("/api/simulate", json={
        "capital": 100.0, "risk_pct": 1.0, "stop_pct": 5.0, "rr": 4.0,
        "leverage": 10.0, "fee_model": "futures", "trades": 100,
        "win_rate_pcts": [20.0, 50.0], "n_sims": 200, "bust_pct": 10.0,
    })
    assert r.status_code == 200
    body = r.json()
    assert [row["wr"] for row in body["rows"]] == [20.0, 50.0]
    row50 = next(x for x in body["rows"] if x["wr"] == 50.0)
    for field in ("mean_net", "p_success", "p_busted", "expectancy", "sharpe"):
        assert field in row50
    assert 0.0 <= row50["p_success"] <= 1.0
    assert 0.0 <= row50["p_busted"] <= 1.0
    # Sharpe at rr 4:1 / WR 50% reproduces the archived report value.
    assert row50["sharpe"] == pytest.approx(0.590, abs=1e-3)
    assert body["summary"]["best_wr"] in (20.0, 50.0)


def test_simulate_is_deterministic_across_requests():
    payload = {"capital": 100.0, "risk_pct": 1.0, "stop_pct": 5.0, "rr": 4.0,
               "leverage": 10.0, "fee_model": "futures", "trades": 100,
               "win_rate_pcts": [50.0], "n_sims": 300}
    first = client.post("/api/simulate", json=payload).json()
    second = client.post("/api/simulate", json=payload).json()
    assert first == second


def test_simulate_rejects_unknown_fee_model():
    r = client.post("/api/simulate", json={"fee_model": "Z"})
    assert r.status_code == 422


def test_simulate_rejects_invalid_numbers():
    for bad in ({"risk_pct": -1}, {"stop_pct": 0}, {"rr": 0}, {"leverage": 0},
                {"n_sims": 0}, {"capital": 0}):
        assert client.post("/api/simulate", json=bad).status_code == 422, bad


def test_simulate_rejects_oversized_request():
    # 20 win rates x 20000 sims x 2000 trades is far past the work limit.
    r = client.post("/api/simulate", json={
        "win_rate_pcts": [float(w) for w in range(20, 40)],
        "n_sims": 20000, "trades": 2000,
    })
    assert r.status_code == 422
    assert "too large" in r.json()["detail"]


def test_simulate_rejects_n_sims_above_cap():
    assert client.post("/api/simulate", json={"n_sims": 20001}).status_code == 422


def test_simulate_rows_carry_kelly_pct():
    r = client.post("/api/simulate", json={
        "capital": 100.0, "risk_pct": 1.0, "stop_pct": 5.0, "rr": 4.0,
        "leverage": 10.0, "fee_model": "futures", "trades": 100,
        "win_rate_pcts": [50.0], "n_sims": 200, "slippage_pct": 0.0,
    })
    assert r.status_code == 200
    row = r.json()["rows"][0]
    assert "kelly_pct" in row
    assert isinstance(row["kelly_pct"], float)
    # 50% at 4:1 is a real edge, so the fraction is strictly positive.
    assert row["kelly_pct"] > 0.0


def test_simulate_slippage_lowers_first_row_mean_net():
    payload = {"capital": 100.0, "risk_pct": 1.0, "stop_pct": 5.0, "rr": 4.0,
               "leverage": 10.0, "fee_model": "futures", "trades": 100,
               "win_rate_pcts": [50.0], "n_sims": 300}
    clean = client.post("/api/simulate", json={**payload, "slippage_pct": 0.0})
    slipped = client.post("/api/simulate", json={**payload, "slippage_pct": 5.0})
    assert clean.status_code == 200
    assert slipped.status_code == 200
    assert slipped.json()["rows"][0]["mean_net"] < clean.json()["rows"][0]["mean_net"]


def test_simulate_rejects_negative_slippage():
    r = client.post("/api/simulate", json={"slippage_pct": -1.0})
    assert r.status_code == 422


def test_simulate_no_longer_accepts_preset():
    # The preset field was removed; an unknown key is ignored, so this must not
    # resurrect the old A/B/C behaviour and must still return the new shape.
    r = client.post("/api/simulate", json={"preset": "A", "n_sims": 10})
    assert r.status_code == 200
    assert "rows" in r.json() and "p_success" in r.json()["rows"][0]


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

def test_simulate_response_echoes_every_request_parameter():
    """Every request field must come back on the response.

    The route already passes these through, but pydantic silently ignores
    undeclared fields, so a missing schema attribute turns the echo into a
    no-op that no other test would notice.
    """
    req = {"capital": 100.0, "risk_pct": 1.0, "stop_pct": 5.0, "rr": 4.0,
           "leverage": 10.0, "fee_model": "futures", "bust_pct": 10.0,
           "slippage_pct": 2.5, "n_sims": 10}
    body = client.post("/api/simulate", json=req).json()
    for field, want in req.items():
        if field in ("n_sims",):
            continue
        assert body[field] == want, (field, body.get(field), want)

def test_simulate_rows_carry_kelly_pct():
    body = client.post("/api/simulate", json={"n_sims": 10, "win_rate_pcts": [50.0]}).json()
    assert isinstance(body["rows"][0]["kelly_pct"], float)
    assert body["summary"]["kelly_wr"] == 50.0
    assert body["summary"]["kelly_half_pct"] == pytest.approx(body["summary"]["kelly_pct"] / 2.0)
