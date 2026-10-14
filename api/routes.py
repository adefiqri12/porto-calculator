"""Route handlers. Each is a thin call into core/ with validated I/O."""
from fastapi import APIRouter, HTTPException

from core import dca, fees, portfolio, rates, sim, trading
from core.presets import PRESETS

from . import schemas

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/presets", response_model=dict[str, schemas.PresetOut])
def get_presets() -> dict:
    return {
        key: schemas.PresetOut(
            key=p.key, label=p.label, sizing=p.sizing, margin=p.margin,
            reward=p.reward, risk=p.risk, leverage=p.leverage,
            fee_model=p.fee_model, rr=p.rr,
        )
        for key, p in PRESETS.items()
    }


@router.post("/cagr", response_model=schemas.CagrResponse)
def post_cagr(req: schemas.CagrRequest) -> schemas.CagrResponse:
    return schemas.CagrResponse(cagr_pct=rates.cagr(req.total_return_pct, req.years))


@router.post("/dca", response_model=schemas.DcaResponse)
def post_dca(req: schemas.DcaRequest) -> schemas.DcaResponse:
    fv = dca.future_value(req.monthly, req.annual_roi_pct, req.months)
    invested = req.monthly * req.months
    rows = dca.yearly_breakdown(req.monthly, req.annual_roi_pct, req.months)
    return schemas.DcaResponse(
        future_value=fv,
        total_invested=invested,
        total_return=fv - invested,
        yearly=[schemas.YearlyRow(**r) for r in rows],
    )


@router.post("/portfolio", response_model=schemas.PortfolioResponse)
def post_portfolio(req: schemas.PortfolioRequest) -> schemas.PortfolioResponse:
    try:
        portfolio.validate_allocation([h.weight_pct for h in req.holdings])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = portfolio.portfolio_future_value(
        req.monthly, req.months, [schemas.to_holding(h) for h in req.holdings]
    )
    return schemas.PortfolioResponse(**result)


@router.post("/trading", response_model=schemas.TradingResponse)
def post_trading(req: schemas.TradingRequest) -> schemas.TradingResponse:
    p = req.win_rate_pct / 100.0
    fee = fees.futures_fee(req.notional) if req.fee_model == "futures" else fees.spot_fee(req.notional)
    stop_distance_pct = req.risk / req.notional * 100.0
    liq_distance = fees.liquidation_distance_pct(req.leverage)
    return schemas.TradingResponse(
        expected_value=trading.expected_value(p, req.reward, req.risk),
        break_even_win_rate_pct=trading.break_even_win_rate(req.reward, req.risk) * 100.0,
        profit_factor=trading.profit_factor(p, req.reward, req.risk),
        sharpe=trading.sharpe_per_trade(p, req.reward, req.risk, fee),
        net_profit=trading.net_profit(p, req.reward, req.risk, fee, req.trades),
        fee_per_trade=fee,
        liquidation_distance_pct=liq_distance,
        liquidation_warning=stop_distance_pct > 0.8 * abs(liq_distance),
    )


@router.post("/simulate", response_model=schemas.SimulateResponse)
def post_simulate(req: schemas.SimulateRequest) -> schemas.SimulateResponse:
    if req.preset not in PRESETS:
        raise HTTPException(status_code=422, detail=f"unknown preset: {req.preset}")
    rows = sim.sweep_win_rates(req.preset, req.win_rate_pcts, req.capital, req.trades)
    capital_rows = sim.capital_scaling(req.preset, [100.0, 500.0, 1000.0], 50.0, req.trades)
    mid = min(rows, key=lambda r: abs(r["wr"] - 50.0))
    best_sharpe = max(
        ({"strategy": "A", "sharpe": mid["sh_a"]}, {"strategy": "C", "sharpe": mid["sh_c"]}),
        key=lambda d: d["sharpe"],
    )
    best_net = max(
        ({"strategy": "A", "net": mid["net_a"]},
         {"strategy": "B", "net": mid["net_b"]},
         {"strategy": "C", "net": mid["net_c"]}),
        key=lambda d: d["net"],
    )
    return schemas.SimulateResponse(
        rows=rows, capital_rows=capital_rows,
        best_by_sharpe=best_sharpe, best_by_net=best_net,
    )
