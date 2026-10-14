"""Route handlers. Each is a thin call into core/ with validated I/O."""
from fastapi import APIRouter, HTTPException

from core import dca, fees, mc, portfolio, rates, trading
from core.presets import PRESETS

from . import schemas

router = APIRouter(prefix="/api")

# The simulation is pure Python and runs at roughly this rate. Measured at
# 1.5-1.7M paths/second under real load (an idle machine measures higher), so
# this is deliberately the conservative end: a cost estimate that runs slow is
# safer than one that promises a speed the machine will not deliver.
PATHS_PER_SECOND = 1_500_000

# A request this long is accepted but is slow enough to be worth warning about.
# It is a UX guard, not a correctness one: `post_simulate` is a sync `def`, so
# FastAPI runs it in a threadpool and a long request does not block the event
# loop or other requests.
MAX_SIMULATE_SECONDS = 60.0
MAX_TOTAL_PATHS = int(PATHS_PER_SECOND * MAX_SIMULATE_SECONDS)


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


def simulate_cost(rows: int, n_sims: int, trades: int) -> int:
    """Simulated trades in a request, the unit of work the guard measures."""
    return rows * n_sims * trades


def check_simulate_size(rows: int, n_sims: int, trades: int) -> None:
    """Refuse a simulation big enough to be unreasonable.

    Raises ``HTTPException`` 422, naming the three inputs and the estimated wall
    clock cost. The raw product of three numbers is not something a user can
    reason about, so the message says which field drove the cost.
    """
    total_paths = simulate_cost(rows, n_sims, trades)
    if total_paths > MAX_TOTAL_PATHS:
        seconds = total_paths / PATHS_PER_SECOND
        raise HTTPException(
            status_code=422,
            detail=(
                f"simulation too large: {rows} win rates x "
                f"{n_sims:,} simulations x {trades:,} trades = "
                f"{total_paths:,} simulated trades, about {seconds:.0f}s of "
                f"work. The limit is about {MAX_SIMULATE_SECONDS:.0f}s "
                f"({MAX_TOTAL_PATHS:,} trades). Reduce the number of "
                f"simulations, trades, or win-rate steps."
            ),
        )


@router.post("/simulate", response_model=schemas.SimulateResponse)
def post_simulate(req: schemas.SimulateRequest) -> schemas.SimulateResponse:
    if req.fee_model not in ("futures", "spot"):
        raise HTTPException(status_code=422, detail=f"unknown fee_model: {req.fee_model}")
    # A careless combination of rows, simulations, and trades can ask for
    # minutes of work. Refuse the genuinely unreasonable before doing any of it.
    check_simulate_size(len(req.win_rate_pcts), req.n_sims, req.trades)
    try:
        rows = mc.sweep(
            capital=req.capital,
            risk_pct=req.risk_pct,
            stop_pct=req.stop_pct,
            rr=req.rr,
            leverage=req.leverage,
            fee_model=req.fee_model,
            trades=req.trades,
            win_rate_pcts=req.win_rate_pcts,
            n_sims=req.n_sims,
            bust_pct=req.bust_pct,
            slippage_pct=req.slippage_pct,
        )
        summary = mc.summarise(rows)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return schemas.SimulateResponse(
        rows=[schemas.SimulateRow(**r) for r in rows],
        summary=summary,
        capital=req.capital,
        risk_pct=req.risk_pct,
        stop_pct=req.stop_pct,
        rr=req.rr,
        leverage=req.leverage,
        fee_model=req.fee_model,
        bust_pct=req.bust_pct,
        slippage_pct=req.slippage_pct,
    )
