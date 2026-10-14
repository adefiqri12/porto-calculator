# Porto Calculator Implementation Plan

> **STATUS: executed.** All 14 tasks landed. 129 tests pass. The app runs from
> `.venv/bin/uvicorn api.app:create_app --factory --port 8000`. See
> "Post-execution corrections" at the end of this file for what the plan got
> wrong; the body below is left as written, not retro-edited.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify four loose CLI scripts and two frozen HTML reports into one offline browser calculator for stock/crypto investing and trading math, with a pure-Python core, a thin FastAPI JSON API, and a no-build static frontend.

**Architecture:** Three layers, one-way dependency `web → api → core`. `core/` holds every formula and imports nothing from the web. `api/` is a thin FastAPI wrapper with Pydantic validation. `web/` is vanilla JS + canvas, no build step, no CDN. The port is proven correct by golden fixtures copied from the existing HTML data arrays.

**Tech Stack:** Python 3.15, FastAPI, Pydantic v2, Uvicorn, pytest, httpx (TestClient). Frontend: vanilla JS, canvas, `Intl.NumberFormat`. No Node, no pandas, no numpy, no CDN.

**Spec:** `docs/superpowers/specs/2026-10-14-porto-calculator-design.md`

## Global Constraints

- Python 3.15; virtualenv at `.venv`.
- Runtime deps: `fastapi`, `uvicorn[standard]`, `pydantic`. Dev deps: `pytest`, `httpx`.
- **No pandas, no numpy.** `core/` uses the stdlib `math` module only.
- **`core/` must not import `fastapi`, `starlette`, or anything web-related.** Enforced by `tests/test_core_is_pure.py`.
- **No network at runtime. No CDN links in `web/`.** Everything served locally.
- **Percent convention:** every parameter or field named `*_pct` is a percentage (e.g. `50.0`, `12.0`). Decimal fractions are used only for local variables named without `_pct` (e.g. `monthly_rate`). This is the single most bug-prone rule; follow it exactly.
- Currency defaults to IDR; UI strings default to Indonesian. Both togglable.
- Charts render with a dependency-free canvas helper. No chart library.
- Commits: one per task, `feat:` / `test:` / `docs:` / `chore:` prefixes.

## Review Focus

These are the input classes and failure modes the spec implies but no formula in it exercises. Each is pinned by a test in the task that owns the code. Most likely to bite first:

1. **`annual_roi_pct = 0`** in DCA — `r = 0` makes `((1+r)**n - 1)/r` a divide-by-zero. A user entering 0% ROI should get `monthly * months`, not a crash. (Task 3)
2. **`win_rate_pct = 0` or `100`** — `std_per_trade` becomes 0, so Sharpe divides by zero. Should return `0.0` (or `inf` explicitly chosen), never `ZeroDivisionError`. (Task 6)
3. **`holdings = []`** in portfolio — an empty allocation should return total 0 and no crash. (Task 4)
4. **`reward = 0` and `risk = 0`** — `break_even_win_rate` and `profit_factor` both divide by zero. Must raise a clear `ValueError`, not emit `nan`. (Task 6)
5. **`months = 0`** — `yearly_breakdown` should return `[]` and `future_value` should return `0.0`, not loop or divide by zero. (Task 3)

---

### Task 1: Project skeleton

**Files:**
- Create: `pyproject.toml`, `core/__init__.py`, `api/__init__.py`, `tests/__init__.py`, `.gitignore` (append)
- Create: `tests/test_core_is_pure.py`

**Interfaces:**
- Produces: importable packages `core` and `api`; a working `.venv`; `pytest` configured with `testpaths = ["tests"]`.

- [ ] **Step 1: Create the venv and install deps**

```bash
cd /media/ade/Data/Python/porto-calculator
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install fastapi "uvicorn[standard]" pydantic pytest httpx
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "porto-calculator"
version = "0.1.0"
requires-python = ">=3.15"
dependencies = ["fastapi", "uvicorn[standard]", "pydantic"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Write the purity test**

```python
# tests/test_core_is_pure.py
import pathlib

FORBIDDEN = ("fastapi", "starlette", "uvicorn", "pydantic")

def test_core_has_no_web_imports():
    offenders = []
    for path in pathlib.Path("core").rglob("*.py"):
        text = path.read_text()
        for line in text.splitlines():
            s = line.strip()
            if s.startswith(("import ", "from ")) and any(f in s for f in FORBIDDEN):
                offenders.append(f"{path}: {s}")
    assert offenders == [], offenders
```

- [ ] **Step 4: Run it**

Run: `.venv/bin/pytest tests/test_core_is_pure.py -v`
Expected: PASS (vacuously — `core/` is empty except `__init__.py`).

- [ ] **Step 5: Append to `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml core/__init__.py api/__init__.py tests/ .gitignore
git commit -m "chore: project skeleton with venv and purity test"
```

---

### Task 2: `core/rates.py` — CAGR and rate conversion

**Files:**
- Create: `core/rates.py`
- Test: `tests/test_rates.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `cagr(total_return_pct: float, years: float) -> float` — returns CAGR as a percent.
  - `annual_to_monthly(annual_pct: float) -> float` — returns a decimal monthly rate.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rates.py
import pytest
from core.rates import cagr, annual_to_monthly

def test_cagr_matches_manual_computation():
    # (1 + 1.50) ** (1/5) - 1 = 0.2011244...  -> 20.11244 %
    assert cagr(150.0, 5) == pytest.approx(20.11244, rel=1e-5)

def test_cagr_single_year_is_identity():
    assert cagr(20.0, 1) == pytest.approx(20.0)

def test_cagr_zero_return():
    assert cagr(0.0, 10) == pytest.approx(0.0)

def test_annual_to_monthly():
    assert annual_to_monthly(12.0) == pytest.approx(0.01)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_rates.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.rates'`

- [ ] **Step 3: Implement `core/rates.py`**

```python
def cagr(total_return_pct: float, years: float) -> float:
    r = total_return_pct / 100.0
    return ((1.0 + r) ** (1.0 / years) - 1.0) * 100.0

def annual_to_monthly(annual_pct: float) -> float:
    return annual_pct / 100.0 / 12.0
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_rates.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add core/rates.py tests/test_rates.py
git commit -m "feat: core CAGR and annual-to-monthly rate conversion"
```

---

### Task 3: `core/dca.py` — DCA future value

**Files:**
- Create: `core/dca.py`
- Test: `tests/test_dca.py`

**Interfaces:**
- Consumes: `core.rates.annual_to_monthly`.
- Produces:
  - `future_value(monthly: float, annual_roi_pct: float, months: int) -> float`
  - `yearly_breakdown(monthly: float, annual_roi_pct: float, months: int) -> list[dict]` with keys `year`, `contributed`, `value`, `return`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_dca.py
import pytest
from core.dca import future_value, yearly_breakdown

def test_future_value_matches_manual():
    # r = 0.01, n = 12 -> 1e6 * ((1.01**12 - 1)/0.01) * 1.01 = 12809328.0433
    assert future_value(1_000_000, 12.0, 12) == pytest.approx(12_809_328.0433, rel=1e-6)

def test_zero_roi_returns_principal_only():
    # Review Focus #1: r == 0 must not divide by zero
    assert future_value(1000, 0.0, 12) == pytest.approx(12_000.0)

def test_zero_months_returns_zero():
    # Review Focus #5
    assert future_value(1000, 12.0, 0) == pytest.approx(0.0)

def test_yearly_breakdown_length_and_totals():
    rows = yearly_breakdown(1_000_000, 12.0, 24)
    assert len(rows) == 2
    assert rows[-1]["contributed"] == pytest.approx(24_000_000)
    assert rows[-1]["value"] == pytest.approx(future_value(1_000_000, 12.0, 24))

def test_yearly_breakdown_zero_months_is_empty():
    # Review Focus #5
    assert yearly_breakdown(1000, 12.0, 0) == []
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_dca.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.dca'`

- [ ] **Step 3: Implement `core/dca.py`**

`future_value` guard: if `months == 0` return `0.0`; if `monthly_rate == 0` return `monthly * months`; else the spec formula. `yearly_breakdown` loops `year in range(1, months // 12 + 1)` and calls `future_value(monthly, annual_roi_pct, year * 12)` for each row, with `contributed = monthly * year * 12` and `return = value - contributed`.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_dca.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add core/dca.py tests/test_dca.py
git commit -m "feat: core DCA future value with zero-rate and zero-month guards"
```

---

### Task 4: `core/presets.py`, `api/schemas.py`, and `core/portfolio.py`

**Files:**
- Create: `core/presets.py`, `core/portfolio.py` (Pydantic schemas live in `api/schemas.py`, created in Task 8, so `core/` stays web-free)
- Test: `tests/test_portfolio.py`

**Interfaces:**
- Consumes: `core.dca.future_value`.
- Produces (in `core/presets.py`): the `StrategyPreset` dataclass and the constant `PRESETS: dict[str, StrategyPreset]` with keys `"A"`, `"B"`, `"C"`, `"fomo"`.
- Produces (in `api/schemas.py`, Task 8): Pydantic models `CagrRequest`, `CagrResponse`, `DcaRequest`, `DcaResponse`, `PortfolioRequest`, `PortfolioResponse`, `TradingRequest`, `TradingResponse`, `SimulateRequest`, `SimulateResponse`, `PresetOut`. `Holding` is a plain dataclass in `core/portfolio.py`.
- Produces (in `core/portfolio.py`):
  - `validate_allocation(weights: list[float]) -> None` — raises `ValueError` unless each `>= 0` and `abs(sum - 100) <= 0.01`.
  - `portfolio_future_value(monthly: float, months: int, holdings: list[Holding]) -> dict` with keys `total_fv`, `per_asset` (list of `{name, weight_pct, future_value}`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_portfolio.py
import pytest
from core.portfolio import Holding
from core.portfolio import validate_allocation, portfolio_future_value

def test_valid_allocation_passes():
    validate_allocation([60.0, 30.0, 10.0])

def test_allocation_within_tolerance_passes():
    validate_allocation([60.0, 30.0, 10.005])  # within 0.01

def test_allocation_summing_wrong_raises():
    with pytest.raises(ValueError):
        validate_allocation([60.0, 30.0, 20.0])

def test_negative_weight_raises():
    with pytest.raises(ValueError):
        validate_allocation([110.0, -10.0])

def test_empty_holdings_returns_zero():
    # Review Focus #3
    result = portfolio_future_value(1000, 12, [])
    assert result["total_fv"] == 0.0
    assert result["per_asset"] == []

def test_weights_split_the_monthly_contribution():
    holdings = [Holding(name="BBCA", weight_pct=50.0, annual_roi_pct=12.0),
                Holding(name="ETH",  weight_pct=50.0, annual_roi_pct=24.0)]
    result = portfolio_future_value(1_000_000, 12, holdings)
    assert result["per_asset"][0]["future_value"] < result["per_asset"][1]["future_value"]
    assert result["total_fv"] == pytest.approx(
        sum(a["future_value"] for a in result["per_asset"]))
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_portfolio.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.portfolio'`

- [ ] **Step 3: Implement `core/presets.py`**

Define the Pydantic models listed in Interfaces with field constraints: `months: int = Field(gt=0)` on `DcaRequest`/`PortfolioRequest`, `win_rate_pct: float = Field(ge=0, le=100)` on `TradingRequest`, `leverage: float = Field(ge=1)`, `capital: float = Field(gt=0)`, `trades: int = Field(gt=0)`, `holdings: list[Holding]`. Define `PRESETS` with the exact values from spec §5.7:

| key | sizing | reward | risk | rr | leverage |
|---|---|---|---|---|---|
| A | fixed $2 | 4.0 | 1.0 | 4.0 | 10 |
| B | 2% compounding | 4.0 | 1.0 | 4.0 | 10 |
| C | fixed $2 | 10.0 | 1.8 | 5.5556 | 10 |
| fomo | spot | 4.0 | 1.0 | 4.0 | 1 |

- [ ] **Step 4: Implement `core/portfolio.py`**

`portfolio_future_value` calls `future_value(monthly * h.weight_pct / 100, h.annual_roi_pct, months)` per holding and sums. Empty list returns `{"total_fv": 0.0, "per_asset": []}`.

- [ ] **Step 5: Run to verify pass**

Run: `.venv/bin/pytest tests/test_portfolio.py -v`
Expected: PASS (6 tests).

- [ ] **Step 6: Commit**

```bash
git add core/presets.py core/portfolio.py tests/test_portfolio.py tests/test_presets.py
git commit -m "feat: Pydantic models, presets, and portfolio allocation math"
```

---

### Task 5: `core/fees.py` — fee models and liquidation

**Files:**
- Create: `core/fees.py`
- Test: `tests/test_fees.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `percent_fee(notional: float, pct: float, sides: int = 2) -> float`
  - `min_fee(notional: float, pct: float, floor: float, sides: int = 2) -> float`
  - `futures_fee(notional: float) -> float`
  - `spot_fee(notional: float) -> float`
  - `liquidation_price(entry: float, leverage: float, side: str = "long") -> float`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_fees.py
import pytest
from core.fees import percent_fee, min_fee, futures_fee, spot_fee, liquidation_price

def test_futures_fee_on_20_notional():
    assert futures_fee(20.0) == pytest.approx(0.026)

def test_spot_fee_uses_floor_on_small_position():
    assert spot_fee(2.0) == pytest.approx(1.90)

def test_spot_fee_is_percent_above_break_even():
    # 0.5% of 1000 = 5.0 per side, above the 0.95 floor
    assert spot_fee(1000.0) == pytest.approx(10.0)

def test_spot_fee_at_break_even_notional():
    # 190 * 0.005 = 0.95 exactly
    assert spot_fee(190.0) == pytest.approx(1.90)

def test_liquidation_distance_at_10x():
    assert liquidation_price(100.0, 10) == pytest.approx(90.0)

def test_liquidation_short_is_mirrored():
    assert liquidation_price(100.0, 10, side="short") == pytest.approx(110.0)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_fees.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.fees'`

- [ ] **Step 3: Implement `core/fees.py`**

`percent_fee = notional * pct / 100 * sides`. `min_fee = max(notional * pct / 100, floor) * sides`. `futures_fee(notional) = notional * (0.05/100 * 2 + 0.03/100)` — taker both sides plus 0.03% funding. `spot_fee(notional) = min_fee(notional, 0.5, 0.95, sides=2)`. `liquidation_price` returns `entry * (1 - 1/leverage)` for long, `entry * (1 + 1/leverage)` for short.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_fees.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add core/fees.py tests/test_fees.py
git commit -m "feat: futures and spot fee models with liquidation distance"
```

---

### Task 6: `core/trading.py` — expectation, break-even, Sharpe

**Files:**
- Create: `core/trading.py`
- Test: `tests/test_trading.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `expected_value(win_rate: float, reward: float, risk: float) -> float` — `win_rate` is a decimal fraction in `[0, 1]`.
  - `break_even_win_rate(reward: float, risk: float) -> float` — decimal.
  - `profit_factor(win_rate: float, reward: float, risk: float) -> float`
  - `std_per_trade(win_rate: float, reward: float, risk: float) -> float`
  - `sharpe_per_trade(win_rate: float, reward: float, risk: float, fee: float = 0.0) -> float` — **non-annualised**.
  - `net_profit(win_rate: float, reward: float, risk: float, fee: float, trades: int) -> float`
  - `gross_profit(win_rate: float, reward: float, risk: float, trades: int) -> float`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_trading.py
import pytest
from core.trading import (expected_value, break_even_win_rate, profit_factor,
                          std_per_trade, sharpe_per_trade, net_profit, gross_profit)

def test_expected_value_strategy_a():
    # 0.5*4 - 0.5*1 = 1.5
    assert expected_value(0.5, 4.0, 1.0) == pytest.approx(1.5)

def test_break_even_win_rate_for_rr_4():
    assert break_even_win_rate(4.0, 1.0) == pytest.approx(0.2)

def test_profit_factor_at_50pct():
    assert profit_factor(0.5, 4.0, 1.0) == pytest.approx(4.0)

def test_std_per_trade_strategy_a():
    assert std_per_trade(0.5, 4.0, 1.0) == pytest.approx(2.5)

def test_sharpe_matches_golden_strategy_a():
    # spec 9.1: shA @ WR50 = 0.590
    assert sharpe_per_trade(0.5, 4.0, 1.0, fee=0.026) == pytest.approx(0.590, abs=1e-3)

def test_sharpe_matches_golden_strategy_c():
    # spec 9.1: shC @ WR50 = 0.691
    assert sharpe_per_trade(0.5, 10.0, 1.8, fee=0.026) == pytest.approx(0.691, abs=1e-3)

def test_net_profit_golden_a_and_c():
    assert net_profit(0.5, 4.0, 1.0, 0.026, 100) == pytest.approx(147.40, abs=0.01)
    assert net_profit(0.5, 10.0, 1.8, 0.026, 100) == pytest.approx(407.40, abs=0.01)

def test_gross_profit_golden_a():
    assert gross_profit(0.5, 4.0, 1.0, 100) == pytest.approx(150.0)

def test_zero_or_hundred_win_rate_sharpe_is_zero():
    # Review Focus #2: std == 0 must not divide by zero
    assert sharpe_per_trade(0.0, 4.0, 1.0, fee=0.026) == 0.0
    assert sharpe_per_trade(1.0, 4.0, 1.0, fee=0.026) == 0.0

def test_zero_reward_and_risk_raises():
    # Review Focus #4
    with pytest.raises(ValueError):
        break_even_win_rate(0.0, 0.0)
    with pytest.raises(ValueError):
        profit_factor(0.5, 0.0, 0.0)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_trading.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.trading'`

- [ ] **Step 3: Implement `core/trading.py`**

Formulas from spec §5.5. `std_per_trade` uses gross payoffs `reward` / `-risk`. `sharpe_per_trade` returns `0.0` when `std_per_trade == 0`. `break_even_win_rate` and `profit_factor` raise `ValueError("reward and risk cannot both be zero")` when `reward == 0 and risk == 0`.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_trading.py -v`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add core/trading.py tests/test_trading.py
git commit -m "feat: trading expectation, break-even WR, profit factor, per-trade Sharpe"
```

---

### Task 7: `core/sim.py` — sweeps, compounding, capital scaling

**Files:**
- Create: `core/sim.py`
- Test: `tests/test_sim.py`

**Interfaces:**
- Consumes: `core.trading.*`, `core.presets.PRESETS`.
- Produces:
  - `compound_equity(capital: float, win_rate_pct: float, trades: int, win_mult: float = 1.04, loss_mult: float = 0.99, fee_rate: float = 0.00026) -> float` — returns final capital; profit is `final - capital`. Win/loss events are interleaved deterministically (alternate starting with a win) so results are reproducible.
  - `sweep_win_rates(preset_key: str, win_rate_pcts: list[float], capital: float, trades: int) -> list[dict]` — each row has `wr`, `net_a`, `net_b`, `net_c`, `sh_a`, `sh_c`.
  - `capital_scaling(preset_key: str, capitals: list[float], win_rate_pct: float, trades: int) -> list[dict]` — each row `capital`, `value`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sim.py
import pytest
from core.sim import compound_equity, sweep_win_rates, capital_scaling

def test_compound_equity_matches_golden_b_net():
    # spec 9.1: netB @ WR50 = 319.08 (HTML path differs slightly; 0.5% tolerance)
    profit = compound_equity(100.0, 50.0, 100) - 100.0
    assert profit == pytest.approx(319.08, rel=0.005)

def test_compound_equity_gross_matches_golden_b():
    # spec 9.1: grossB @ WR50 = 329.96
    profit = compound_equity(100.0, 50.0, 100, fee_rate=0.0) - 100.0
    assert profit == pytest.approx(329.96, rel=0.005)

def test_sweep_rows_match_golden_table():
    rows = sweep_win_rates("A", [20.0, 50.0, 60.0], 100.0, 100)
    assert [r["wr"] for r in rows] == [20.0, 50.0, 60.0]
    assert rows[0]["net_a"] == pytest.approx(-2.60, abs=0.01)
    assert rows[1]["net_a"] == pytest.approx(147.40, abs=0.01)
    assert rows[1]["sh_a"] == pytest.approx(0.590, abs=1e-3)
    assert rows[2]["net_c"] == pytest.approx(525.40, abs=0.01)

def test_capital_scaling_matches_golden():
    # spec 9.2: aPct @ $500 = 737.00, bPct @ $500 = 1595.38
    rows = capital_scaling("A", [100.0, 500.0], 50.0, 100)
    assert rows[1]["value"] == pytest.approx(737.00, rel=0.005)
    rows_b = capital_scaling("B", [100.0, 500.0], 50.0, 100)
    assert rows_b[1]["value"] == pytest.approx(1595.38, rel=0.005)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_sim.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.sim'`

- [ ] **Step 3: Implement `core/sim.py`**

`compound_equity` builds the interleaved win/loss sequence, applies `win_mult`/`loss_mult`, then subtracts `fee_rate * capital` per trade. `sweep_win_rates` computes, per win rate, `net_a` (fixed $2 sizing: `trades * (EV_a - fee_a)` where `fee_a = 0.026`), `net_b` (via `compound_equity`), `net_c` (`trades * (EV_c - fee_c)`), `sh_a` and `sh_c` via `sharpe_per_trade`. `capital_scaling` scales percentage sizing linearly and leaves fixed sizing constant, per spec §9.2.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_sim.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add core/sim.py tests/test_sim.py
git commit -m "feat: win-rate sweep, compounding equity, capital scaling"
```

---

### Task 8: FastAPI application

**Files:**
- Create: `api/app.py`, `api/routes.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: everything in `core/`.
- Produces: `api.app.create_app() -> FastAPI` with routes `GET /api/health`, `GET /api/presets`, `POST /api/cagr`, `POST /api/dca`, `POST /api/portfolio`, `POST /api/trading`, `POST /api/simulate`, and a `StaticFiles` mount at `/` serving `web/`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from api.app import create_app

client = TestClient(create_app())

def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}

def test_presets_has_four_strategies():
    body = client.get("/api/presets").json()
    assert set(body) == {"A", "B", "C", "fomo"}

def test_cagr_endpoint():
    r = client.post("/api/cagr", json={"total_return_pct": 150.0, "years": 5})
    assert r.status_code == 200
    assert r.json()["cagr_pct"] == pytest.approx(20.11244, rel=1e-5)

def test_dca_endpoint():
    r = client.post("/api/dca", json={"monthly": 1_000_000, "annual_roi_pct": 12.0, "months": 12})
    assert r.status_code == 200
    assert r.json()["future_value"] == pytest.approx(12_809_328.0433, rel=1e-6)

def test_trading_endpoint_matches_golden():
    r = client.post("/api/trading", json={
        "win_rate_pct": 50.0, "reward": 4.0, "risk": 1.0,
        "leverage": 10.0, "fee_model": "futures", "capital": 100.0, "trades": 100})
    assert r.status_code == 200
    assert r.json()["net_profit"] == pytest.approx(147.40, abs=0.01)

def test_invalid_months_rejected():
    r = client.post("/api/dca", json={"monthly": 1000, "annual_roi_pct": 12.0, "months": 0})
    assert r.status_code == 422

def test_invalid_win_rate_rejected():
    r = client.post("/api/trading", json={
        "win_rate_pct": 150.0, "reward": 4.0, "risk": 1.0,
        "leverage": 10.0, "fee_model": "futures", "capital": 100.0, "trades": 100})
    assert r.status_code == 422
```

Add `import pytest` at the top of the test file.

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.app'`

- [ ] **Step 3: Implement `api/routes.py` and `api/app.py`**

Each route is a thin call into `core/` with the request model as its parameter and the response model as its return annotation, so `/docs` is accurate. `create_app()` registers the routers and mounts `StaticFiles(directory="web", html=True)` at `/`. `GET /api/presets` returns `core.presets.PRESETS` serialised.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_api.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Verify `/docs` and the server boot**

Run: `.venv/bin/uvicorn api.app:create_app --factory --port 8000 &` then `curl -s localhost:8000/api/health` and `curl -s -o /dev/null -w "%{http_code}" localhost:8000/docs`
Expected: `{"status":"ok"}` and `200`. Kill the server.

- [ ] **Step 6: Commit**

```bash
git add api/ tests/test_api.py
git commit -m "feat: FastAPI endpoints for cagr, dca, portfolio, trading, simulate"
```

---

### Task 9: Frontend shell — layout, charts, API client

**Files:**
- Create: `web/index.html`, `web/styles.css`, `web/charts.js`, `web/app.js`, `web/i18n.js`
- Test: `tests/test_web_assets.py`

**Interfaces:**
- Consumes: the API from Task 8.
- Produces: `charts.js` exposing `barChart(canvasEl, labels, series, opts)` and `lineChart(canvasEl, labels, series, opts)`; `i18n.js` exposing `t(key)` and `formatMoney(value, currency)`; `app.js` exposing `postJSON(path, body)` and `debounce(fn, ms)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_web_assets.py
import pathlib

def test_web_assets_exist():
    for name in ("index.html", "styles.css", "charts.js", "app.js", "i18n.js"):
        assert pathlib.Path("web", name).is_file(), name

def test_no_cdn_links():
    html = pathlib.Path("web", "index.html").read_text()
    assert "http://" not in html and "https://" not in html

def test_four_tabs_present():
    html = pathlib.Path("web", "index.html").read_text()
    for tab in ("Invest", "Portfolio", "Trading", "Simulate"):
        assert f'data-tab="{tab}"' in html

def test_shared_formula_symbols_absent_from_js():
    # charts.js must not duplicate the math; it only draws
    js = pathlib.Path("web", "charts.js").read_text()
    assert "1.04" not in js and "0.026" not in js
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_web_assets.py -v`
Expected: FAIL — files do not exist.

- [ ] **Step 3: Implement the shell**

`index.html`: header with currency (IDR/USD) and language (id/en) toggles, four tab buttons carrying `data-tab="Invest|Portfolio|Trading|Simulate"`, four `<section>` panels, canvas elements. Reuse the dark palette from `trading-simulation/binance-futures.html` (`--bg:#0e1116`, `--panel:#161b22`, `--line:#2a3340`, `--tx:#e6edf3`, accents `--a:#58a6ff`, `--b:#3fb950`, `--c:#f0883e`). `charts.js`: dependency-free canvas bar/line renderer modelled on the `barChart` already in the HTML reports. `app.js`: `postJSON`, `debounce`, tab switching, and a `render()` per tab that is stubbed in this task.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_web_assets.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Manual browser check**

Run: `.venv/bin/uvicorn api.app:create_app --factory --port 8000`
Expected: `http://localhost:8000/` shows the dark page with four tabs; clicking tabs switches panels; browser console has no errors. Stop the server.

- [ ] **Step 6: Commit**

```bash
git add web/ tests/test_web_assets.py
git commit -m "feat: frontend shell with tabs, canvas charts, api client"
```

---

### Task 10: Invest tab

**Files:**
- Modify: `web/index.html`, `web/app.js`

**Interfaces:**
- Consumes: `POST /api/cagr`, `POST /api/dca`; `postJSON`, `debounce`, `barChart`.
- Produces: `renderInvest()` in `app.js`.

- [ ] **Step 1: Wire the Invest panel**

Inputs: total return %, years, monthly amount, annual ROI %, months. On change (150 ms debounce): `POST /api/cagr` and `POST /api/dca`; render a CAGR card, a summary card row (future value, total invested, total return), the yearly table from `yearly[]`, and a bar chart of yearly values.

- [ ] **Step 2: Verify in the browser**

Run: `.venv/bin/uvicorn api.app:create_app --factory --port 8000`
Expected: entering monthly `1000000`, ROI `12`, months `12` shows future value `12,809,328.04` (IDR formatted) and a 1-row yearly table; changing months to `24` adds a second row without a page reload. Stop the server.

- [ ] **Step 3: Commit**

```bash
git add web/index.html web/app.js
git commit -m "feat: Invest tab with CAGR, DCA summary, and yearly chart"
```

---

### Task 11: Portfolio tab

**Files:**
- Modify: `web/index.html`, `web/app.js`

**Interfaces:**
- Consumes: `POST /api/portfolio`; `postJSON`, `debounce`, `barChart`.
- Produces: `renderPortfolio()` in `app.js`.

- [ ] **Step 1: Wire the Portfolio panel**

Editable rows (name, weight %, annual ROI %), add/remove row buttons, a live weight-sum indicator that turns red unless the sum is `100 ± 0.01`, and a "Calculate" action. On success: render per-asset future values and the total, plus a bar chart. On 422, show the returned field error inline.

- [ ] **Step 2: Verify in the browser**

Run: `.venv/bin/uvicorn api.app:create_app --factory --port 8000`
Expected: rows summing to 90 show a red indicator and the request is blocked client-side; summing to 100 returns results; `BBCA` at 12% ROI yields less than `ETH` at 24% ROI for equal weights. Stop the server.

- [ ] **Step 3: Commit**

```bash
git add web/index.html web/app.js
git commit -m "feat: Portfolio tab with live allocation validation"
```

---

### Task 12: Trading tab

**Files:**
- Modify: `web/index.html`, `web/app.js`

**Interfaces:**
- Consumes: `GET /api/presets`, `POST /api/trading`; `postJSON`, `debounce`, `barChart`.
- Produces: `renderTrading()` in `app.js`.

- [ ] **Step 1: Wire the Trading panel**

Preset selector A/B/C/fomo (loaded from `/api/presets`), win-rate slider, fee-model selector (futures/spot), leverage, capital, trades. On change: `POST /api/trading`; render EV, break-even WR, profit factor, Sharpe, net profit; mark the break-even WR on the win-rate slider; show a red liquidation warning when the liquidation distance is smaller than the stop distance (preset C at 10x).

- [ ] **Step 2: Verify in the browser**

Run: `.venv/bin/uvicorn api.app:create_app --factory --port 8000`
Expected: preset A, WR 50, 100 trades, $100 shows net profit `147.40` and Sharpe `0.590`; preset C shows the liquidation warning; break-even marker sits at 20% for A. Stop the server.

- [ ] **Step 3: Commit**

```bash
git add web/index.html web/app.js
git commit -m "feat: Trading tab with presets, break-even marker, liquidation warning"
```

---

### Task 13: Simulate tab

**Files:**
- Modify: `web/index.html`, `web/app.js`

**Interfaces:**
- Consumes: `POST /api/simulate`; `postJSON`, `debounce`, `lineChart`, `barChart`.
- Produces: `renderSimulate()` in `app.js`.

- **Step 1: Wire the Simulate panel**

Win-rate range control (default 20-60%), capital selector ($100/$500/$1000), trades. On change: `POST /api/simulate`; render the A/B/C comparison table, a multi-series chart, and "best by Sharpe" / "best by net" callouts. Include the capital-scaling view from spec §9.2.

- [ ] **Step 2: Verify in the browser**

Run: `.venv/bin/uvicorn api.app:create_app --factory --port 8000`
Expected: the table matches spec §9.1 at WR 20/40/50/60; switching capital to $500 reproduces spec §9.2; best-by-Sharpe and best-by-net callouts update. Stop the server.

- [ ] **Step 3: Commit**

```bash
git add web/index.html web/app.js
git commit -m "feat: Simulate tab with win-rate sweep and capital scaling"
```

---

### Task 14: Migration, README, final verification

**Files:**
- Move: `CAGR_calculation.py`, `future_value.py`, `stock_allocation.py`, `risk_to_ratio_trading_calculation.py`, `trading-simulation/` → `archive/`
- Modify: `README.md`

**Interfaces:**
- Consumes: everything.
- Produces: the finished repository.

- [ ] **Step 1: Move the originals into `archive/`**

```bash
git mv CAGR_calculation.py archive/CAGR_calculation.py
git mv future_value.py archive/future_value.py
git mv stock_allocation.py archive/stock_allocation.py
git mv risk_to_ratio_trading_calculation.py archive/risk_to_ratio_trading_calculation.py
git mv trading-simulation archive/trading-simulation
```

- [ ] **Step 2: Rewrite `README.md`**

Sections: what the app is; how to run (`python3 -m venv .venv`, install, `uvicorn api.app:create_app --factory --port 8000`, open `http://localhost:8000`); the module map; the formulas from spec §5; a note that `archive/` holds the originals as reference; how to run tests.

- [ ] **Step 3: Full test run**

Run: `.venv/bin/pytest -v`
Expected: all tests PASS.

- [ ] **Step 4: End-to-end browser pass**

Run: `.venv/bin/uvicorn api.app:create_app --factory --port 8000`
Expected: all four tabs produce the golden numbers from spec §9. Stop the server.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs: migrate originals to archive/ and rewrite README"
```

---

## Self-Review

**1. Spec coverage.** §1-2 intent → Tasks 1, 9-13. §3 architecture → Tasks 1, 8. §4 modules → Tasks 2-8. §5 formulas → Tasks 2-7. §6 API → Task 8. §7 frontend → Tasks 9-13. §8 testing → every task. §9 golden fixtures → Tasks 2-7, 10-13. §10 migration → Task 14. §11 risks → Global Constraints. §12 build order → task order. No gaps.

**2. Step scan.** Each step is one action with a checkable result. Frontend tasks 10-13 use manual browser checks because there is no JS test runner by design (no Node); this is stated rather than hidden. No "handle edge cases" steps.

**3. Type consistency.** `future_value(monthly, annual_roi_pct, months)` is defined in Task 3 and consumed identically in Tasks 4 and 8. `sharpe_per_trade(win_rate, reward, risk, fee)` in Task 6 matches its use in Task 7. `PRESETS` keys `A/B/C/fomo` are used in Tasks 7, 8, 12. `compound_equity` signature in Task 7 matches its test.

**4. Review Focus.** All five uncovered failure modes have tests in their owning tasks: #1 and #5 in Task 3, #2 and #4 in Task 6, #3 in Task 4. None left open.

**5. Proportion.** The plan is longer than the spec because it carries exact signatures and test assertions; code bodies appear only where the signature and tests do not determine the implementation (Task 7's `compound_equity`).

---

## Post-execution corrections

Written after the build, because two of the claims above were wrong.

**1. "No gaps" was overstated.** Task 9 reduced `i18n.js` to `t(key)` plus
`formatMoney`, and no task wired the dictionary through the UI or implemented
`localStorage`. The result shipped with a language toggle that translated 3 of
~45 strings, so Indonesian was the stated default while the UI rendered in
English. Fixed in `3e61581`; the frontend now carries `data-i18n` attributes
and `I18n.apply()`, and `tests/test_i18n.py` fails on any missing key.

**2. The plan's frontend verification was "manual browser checks", which is
weaker than it sounds.** Manual inspection is what missed the i18n gap and, more
seriously, a `global.localStorage` ReferenceError that a try/catch swallowed so
completely that restore was a silent no-op. `tests/cdp_check.py` now drives real
clicks over the Chrome DevTools Protocol and fails on console errors.

**3. Core-purity vs. Pydantic.** Caught during execution, noted for accuracy:
the core-purity test forbids Pydantic in `core/`, but Task 4 put Pydantic models
there. Resolved by splitting `core/presets.py` (stdlib dataclass) from
`api/schemas.py` (Pydantic).
