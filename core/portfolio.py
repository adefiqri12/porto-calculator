"""Portfolio allocation."""
from dataclasses import dataclass

from core.dca import future_value

TOLERANCE = 0.01


@dataclass(frozen=True)
class Holding:
    name: str
    weight_pct: float
    annual_roi_pct: float


def validate_allocation(weights: list[float]) -> None:
    """Raise ValueError unless weights are non-negative and sum to 100."""
    for w in weights:
        if w < 0:
            raise ValueError("weights must be non-negative")
    total = sum(weights)
    if abs(total - 100.0) > TOLERANCE:
        raise ValueError(f"weights must sum to 100 (got {total})")


def portfolio_future_value(monthly: float, months: int, holdings: list[Holding]) -> dict:
    """Split the monthly contribution across holdings by weight, each at its own ROI."""
    if not holdings:
        return {"total_fv": 0.0, "per_asset": []}
    per_asset = []
    for h in holdings:
        fv = future_value(monthly * h.weight_pct / 100.0, h.annual_roi_pct, months)
        per_asset.append(
            {"name": h.name, "weight_pct": h.weight_pct, "future_value": fv}
        )
    total = sum(a["future_value"] for a in per_asset)
    return {"total_fv": total, "per_asset": per_asset}
