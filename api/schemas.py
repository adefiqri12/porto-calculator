"""Pydantic request/response schemas for the HTTP layer.

These live in api/ rather than core/ so that core/ stays free of web
dependencies (enforced by tests/test_core_is_pure.py).
"""
from pydantic import BaseModel, Field

from core.portfolio import Holding


class CagrRequest(BaseModel):
    total_return_pct: float
    years: float = Field(gt=0)


class CagrResponse(BaseModel):
    cagr_pct: float


class DcaRequest(BaseModel):
    monthly: float = Field(ge=0)
    annual_roi_pct: float
    months: int = Field(gt=0)


class YearlyRow(BaseModel):
    year: int
    contributed: float
    value: float
    return_: float = Field(alias="return")

    model_config = {"populate_by_name": True}


class DcaResponse(BaseModel):
    future_value: float
    total_invested: float
    total_return: float
    yearly: list[YearlyRow]


class HoldingIn(BaseModel):
    name: str
    weight_pct: float = Field(ge=0)
    annual_roi_pct: float


class PortfolioRequest(BaseModel):
    monthly: float = Field(ge=0)
    months: int = Field(gt=0)
    holdings: list[HoldingIn] = Field(default_factory=list)


class AssetOut(BaseModel):
    name: str
    weight_pct: float
    future_value: float


class PortfolioResponse(BaseModel):
    total_fv: float
    per_asset: list[AssetOut]


class TradingRequest(BaseModel):
    win_rate_pct: float = Field(ge=0, le=100)
    reward: float = Field(gt=0)
    risk: float = Field(gt=0)
    leverage: float = Field(ge=1)
    fee_model: str = "futures"
    capital: float = Field(gt=0)
    trades: int = Field(gt=0)
    notional: float = Field(default=20.0, gt=0)


class TradingResponse(BaseModel):
    expected_value: float
    break_even_win_rate_pct: float
    profit_factor: float
    sharpe: float
    net_profit: float
    fee_per_trade: float
    liquidation_distance_pct: float
    liquidation_warning: bool


class SimulateRequest(BaseModel):
    capital: float = Field(default=100.0, gt=0)
    risk_pct: float = Field(default=1.0, ge=0, le=100)
    stop_pct: float = Field(default=5.0, gt=0)
    rr: float = Field(default=4.0, gt=0)
    leverage: float = Field(default=10.0, ge=1)
    fee_model: str = "futures"
    trades: int = Field(default=100, gt=0)
    win_rate_pcts: list[float] = Field(default_factory=lambda: [20.0, 30.0, 40.0, 50.0, 60.0])
    n_sims: int = Field(default=1000, gt=0, le=20000)
    bust_pct: float = Field(default=10.0, ge=0)


class SimulateRow(BaseModel):
    wr: float
    mean_final: float
    median_final: float
    mean_net: float
    median_net: float
    p_success: float
    p_busted: float
    expectancy: float
    sharpe: float
    notional: float
    fee_per_trade: float
    n_sims: int


class SimulateResponse(BaseModel):
    rows: list[SimulateRow]
    summary: dict
    capital: float
    risk_pct: float
    stop_pct: float
    rr: float
    leverage: float
    fee_model: str
    bust_pct: float


class PresetOut(BaseModel):
    key: str
    label: str
    sizing: str
    margin: float
    reward: float
    risk: float
    leverage: float
    fee_model: str
    rr: float


def to_holding(h: HoldingIn) -> Holding:
    return Holding(name=h.name, weight_pct=h.weight_pct, annual_roi_pct=h.annual_roi_pct)
