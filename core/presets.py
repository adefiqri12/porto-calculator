"""Strategy presets.

Pure data, stdlib only, so it stays inside the dependency-free core. The
Pydantic request/response schemas live in api/schemas.py instead.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyPreset:
    key: str
    label: str
    sizing: str          # "fixed" | "percent"
    margin: float        # fixed USD margin, or percent of capital when percent
    reward: float
    risk: float
    leverage: float
    fee_model: str       # "futures" | "spot"

    @property
    def rr(self) -> float:
        return self.reward / self.risk


PRESETS: dict[str, StrategyPreset] = {
    "A": StrategyPreset("A", "A - fixed margin $2, 10x", "fixed", 2.0, 4.0, 1.0, 10.0, "futures"),
    "B": StrategyPreset("B", "B - 2% of capital, compounding", "percent", 2.0, 4.0, 1.0, 10.0, "futures"),
    "C": StrategyPreset("C", "C - fixed margin $2, RR 5.56:1", "fixed", 2.0, 10.0, 1.8, 10.0, "futures"),
    "fomo": StrategyPreset("fomo", "fomo.family spot, $0.95 fee floor", "fixed", 2.0, 4.0, 1.0, 1.0, "spot"),
}
