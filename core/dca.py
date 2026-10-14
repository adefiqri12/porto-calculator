"""Dollar-cost-averaging future value."""
from core.rates import annual_to_monthly


def future_value(monthly: float, annual_roi_pct: float, months: int) -> float:
    """Future value of a monthly contribution at a fixed annual ROI.

    Guard: months == 0 -> 0.0. A zero rate degenerates to simple accumulation,
    which is what a user entering 0% ROI expects rather than a divide-by-zero.
    """
    if months <= 0:
        return 0.0
    r = annual_to_monthly(annual_roi_pct)
    if r == 0.0:
        return monthly * months
    return monthly * ((1.0 + r) ** months - 1.0) / r * (1.0 + r)


def yearly_breakdown(monthly: float, annual_roi_pct: float, months: int) -> list[dict]:
    """One row per complete year: contributed, value, return."""
    if months <= 0:
        return []
    rows = []
    for year in range(1, months // 12 + 1):
        contributed = monthly * year * 12
        value = future_value(monthly, annual_roi_pct, year * 12)
        rows.append(
            {
                "year": year,
                "contributed": contributed,
                "value": value,
                "return": value - contributed,
            }
        )
    return rows
