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
    preset: str = "A"
    win_rate_pcts: list[float] = Field(default_factory=lambda: [20.0, 30.0, 40.0, 50.0, 60.0])
    capital: float = Field(default=100.0, gt=0)
    trades: int = Field(default=100, gt=0)


class SimulateResponse(BaseModel):
    rows: list[dict]
    capital_rows: list[dict]
    best_by_sharpe: dict
    best_by_net: dict


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
