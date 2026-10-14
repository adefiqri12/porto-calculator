"""Rate helpers: CAGR and annual-to-monthly conversion."""


def cagr(total_return_pct: float, years: float) -> float:
    """Compound annual growth rate as a percentage.

    total_return_pct is the total return over the whole period, in percent.
    """
    if years <= 0:
        raise ValueError("years must be positive")
    r = total_return_pct / 100.0
    return ((1.0 + r) ** (1.0 / years) - 1.0) * 100.0


def annual_to_monthly(annual_pct: float) -> float:
    """Convert an annual percentage rate to a decimal monthly rate."""
    return annual_pct / 100.0 / 12.0
