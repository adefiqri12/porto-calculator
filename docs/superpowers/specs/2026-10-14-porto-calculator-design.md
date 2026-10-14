# Porto Calculator — Unified Investing & Trading Calculator

**Date:** 2026-10-14
**Status:** Approved (design)
**Approach:** A — pure-Python core + JSON API + no-build static frontend
**Scope:** Calculator only. Offline-capable. No market data, no broker integration.

---

## 1. Problem

The repository is four unrelated CLI scripts plus two frozen HTML reports.

| Current artifact | What it does | Problem |
|---|---|---|
| `CAGR_calculation.py` | CAGR from total return + years | 5 lines, no function, no reuse |
| `future_value.py` | DCA future value, optional CSV export | Formula duplicated elsewhere |
| `stock_allocation.py` | Per-stock DCA with allocation weights | Same DCA formula, copy #2 |
| `risk_to_ratio_trading_calculation.py` | Position sizing from R:R | No connection to anything |
| `trading-simulation/binance-futures.html` | 10x futures A/B/C strategy comparison | Numbers hand-computed and pasted; zero interactivity |
| `trading-simulation/meme-coin.html` | Spot meme-coin fee math | Same; static |

There is no shared vocabulary, no single source of truth for any formula, and no way to change an input and see the result. "Not a unified whole" is accurate.

## 2. Intent

One offline browser application that turns the frozen tables in those HTML files into live controls: move a slider, the table and chart update. Same math, unified, testable.

**Success criteria**

1. Every formula exists in exactly one place in `core/`.
2. Changing any input (win rate, fee, leverage, capital, ROI, months, allocation) updates results in the browser without a page reload.
3. The numbers match the existing HTML reports exactly (see §9 golden fixtures).
4. Runs with one command, no Node, no CDN, no network.
5. Core math is importable and testable without starting a server.

**Non-goals (explicitly out of scope)**

- Historical backtesting (no OHLC downloads).
- Live prices, paper trading, order execution, broker/exchange APIs.
- Accounts, auth, server-side database.
- Tax, inflation, or real-world slippage modelling beyond the flat fee model in §5.

## 3. Architecture

```
porto-calculator/
  core/          pure Python, zero web dependencies
  api/           FastAPI, thin wrappers over core
  web/           index.html, app.js, charts.js, styles.css  (no build step)
  tests/         pytest, golden fixtures from the HTML reports
  legacy/        the original 4 scripts + 2 HTML files, kept as reference
  docs/superpowers/specs/    this document
  pyproject.toml
  README.md
```

Dependency direction is one-way: `web → api → core`. `core` imports nothing from `api` or `web`. That is what makes the math provable in isolation.

## 4. Core modules

| Module | Absorbs | Public functions |
|---|---|---|
| `core/rates.py` | `CAGR_calculation.py` | `cagr(total_return, years)`, `annual_to_monthly(annual_pct)` |
| `core/dca.py` | `future_value.py` | `future_value(monthly, annual_roi_pct, months)`, `yearly_breakdown(...)` |
| `core/portfolio.py` | `stock_allocation.py` | `validate_allocation(weights)`, `portfolio_future_value(...)` |
| `core/fees.py` | hardcoded HTML numbers | `percent_fee(notional, pct, sides)`, `min_fee(notional, pct, floor, sides)`, `funding(notional, pct)`, `liquidation_price(leverage, entry, side)` |
| `core/trading.py` | `risk_to_ratio_*.py` + both HTML | `expected_value(...)`, `break_even_win_rate(rr)`, `profit_factor(...)`, `sharpe_per_trade(...)`, `net_profit(...)` |
| `core/sim.py` | new | `sweep_win_rates(...)`, `equity_curve(...)`, `compound_equity(...)` |
| `core/models.py` | new | Pydantic request/response schemas shared by core and api |

## 5. Domain model — exact definitions

All formulas below were **verified against the existing HTML reports** (see §9). Use these verbatim.

### 5.1 Rates

```
CAGR = (1 + total_return) ** (1 / years) - 1
monthly_rate = annual_roi_pct / 100 / 12
```

### 5.2 DCA future value

```
FV = monthly * ((1 + r)**n - 1) / r * (1 + r)      r = monthly_rate, n = months
total_invested = monthly * n
total_return   = FV - total_invested
```
`r == 0` must return `monthly * n` (guard against divide-by-zero).

### 5.3 Portfolio allocation

- Weights are percentages; `validate_allocation` requires `abs(sum - 100) <= 0.01`, each weight `>= 0`.
- Per-asset future value = `future_value(monthly * weight/100, asset_roi, months)`.
- Portfolio total = sum of per-asset values. Each asset carries its own expected annual ROI.

### 5.4 Fees

Two fee models, both from the existing reports:

```
# Binance futures (percent-based)
taker_pct   = 0.05     # per side
funding_pct = 0.03     # per trade, on notional
fee_futures(notional) = notional * (0.05/100 * 2 + 0.03/100)   # = 0.13% of notional

# fomo.family spot (percent with a floor)
fee_spot(notional) = max(notional * 0.005, 0.95) * 2           # 0.5%/side, min $0.95/tx
```

Leverage and liquidation:

```
notional     = margin * leverage
price_move   = notional * move_pct / leverage    (position P&L)
roi_on_margin = move_pct * leverage
liquidation_price ≈ entry * (1 - 1/leverage)     (long; short mirrored)
```
At 10x, liquidation is ~-10% price move. This matches the warning text in `binance-futures.html`.

### 5.5 Trading expectation

```
EV_per_trade = p * win$ + (1 - p) * lose$          (lose$ is negative)
break_even_win_rate = risk / (risk + reward)       (equivalently 1 / (1 + rr))
profit_factor = (p * reward) / ((1 - p) * risk)
sharpe_per_trade = (EV_per_trade - fee_per_trade) / std_per_trade
std_per_trade = sqrt(p*(win - EV)^2 + (1-p)*(lose - EV)^2)
net_profit(trades) = trades * EV_per_trade - trades * fee_per_trade
```

**Important:** `sharpe_per_trade` is deliberately **not annualised** — that is what reproduces the HTML values (A = 0.590, C = 0.691 at WR 50%). Annualisation (`* sqrt(trades_per_year)`) may be offered as a separate display toggle, clearly labelled. Both a **net** Sharpe (fee deducted from EV) and a **gross** Sharpe (no fee) are shown; the meme-coin report labels these `shA` and `shAg`.

### 5.6 Compounding (strategy B)

Strategy B re-sizes each trade to 2% of current capital, so P&L is multiplicative:

```
win  -> capital *= (1 + 0.04)     # +20% price * 10x leverage * 2% sizing = +4%
loss -> capital *= (1 - 0.01)     # -5% price * 10x * 2% = -1%
per-trade fee = 0.00026 * capital # 0.13% of notional, notional = 0.2 * capital
```
`profit = final_capital - initial_capital`. Note the HTML reports **profit**, not final value. Trade order matters for the fee path; `sim.equity_curve` must apply fees per trade, and `compound_equity` must use a deterministic interleaved win/loss sequence so results are reproducible.

### 5.7 Presets (from the HTML reports)

| Preset | Sizing | Reward | Risk | RR | Notes |
|---|---|---|---|---|---|
| A | fixed $2 margin, 10x | +$4 | -$1 | 4:1 | liq -10% below SL |
| B | 2% of capital, compounding | x1.04 | x0.99 | 4:1 | sizing differs from A |
| C | fixed $2 margin, 10x | +$10 | -$1.8 | 5.56:1 | liq only 1% below SL (danger) |
| fomo spot | position-based | user | user | user | fee floor $0.95 dominates |

## 6. API

FastAPI. Every request body is a Pydantic model from `core/models.py`. Response models are declared so `/docs` is accurate.

```
GET  /                      -> serves web/index.html (StaticFiles)
GET  /api/health            -> {status: "ok"}
GET  /api/presets           -> the A/B/C/fomo presets from §5.7
POST /api/cagr              -> {total_return_pct, years} -> {cagr_pct}
POST /api/dca               -> {monthly, annual_roi_pct, months} -> {future_value, total_invested, total_return, yearly[]}
POST /api/portfolio         -> {monthly, months, holdings:[{name, weight_pct, annual_roi_pct}]} -> {total_fv, per_asset[]}
POST /api/trading           -> {win_rate_pct, reward, risk, leverage, fee_model, capital, trades} -> {ev, break_even_wr, profit_factor, sharpe, net_profit}
POST /api/simulate          -> {preset, win_rate_range, capital, trades} -> {rows[], best_by_sharpe, best_by_net}
```

Validation lives in Pydantic: `months > 0`, `0 <= win_rate_pct <= 100`, `leverage >= 1`, `weights` sum to 100, `capital > 0`. Invalid input returns HTTP 422 with field-level detail; no custom error format.

## 7. Frontend

Four tabs, single page, no framework, no build.

1. **Invest** — CAGR + DCA. Inputs: total return, years, monthly amount, annual ROI, months. Output: summary cards + yearly table + growth chart.
2. **Portfolio** — allocation editor (rows of name / weight / ROI), weight-sum validation shown live, per-asset and total future value.
3. **Trading** — strategy presets A/B/C, win-rate slider, fee model selector, leverage, capital. Output: net/gross profit table across win rates, Sharpe table, break-even marker, liquidation warning when `liq_distance < sl_distance`.
4. **Simulate** — win-rate sweep 20-60% for all presets at once, comparison chart, "best by Sharpe" / "best by net" callouts.

Interaction: input `change`/`input` event -> 150 ms debounce -> `fetch` POST -> re-render table + redraw chart. Charts use a dependency-free canvas bar/line renderer (`web/charts.js`), modelled on the `barChart` already in the HTML reports. No CDN.

Localisation: `web/i18n.js` holds an `id`/`en` string dictionary and an IDR/USD formatter. Default `id` + IDR (matches the majority of existing content); toggle in the header. Number formatting uses `Intl.NumberFormat`.

Persistence: `localStorage` only, for saved scenarios/presets. No server-side storage.

## 8. Testing

`pytest`, run against `core/` only, no server needed.

- **Golden fixtures (§9)** — the exact numbers from the existing HTML reports. This is the strongest evidence the port is correct, because the source values were independently produced.
- **Property tests** — `future_value(0 ROI) == monthly * months`; `break_even_win_rate` makes `EV == 0`; `sharpe` is monotonic in win rate; allocation weights must sum to 100.
- **API tests** — `TestClient` smoke tests that each endpoint returns 200 for valid input and 422 for invalid.
- **Fee tests** — fomo round-trip on a $2 position equals $1.90; futures fee on $20 notional equals $0.026.

## 9. Golden fixtures (verified 2026-10-14)

All values below are copied from the JS data arrays in the existing HTML reports (`binance-futures.html` lines 150-156 and 219-221; `meme-coin.html` lines 116-122) and **independently reproduced** by the formulas in §5. These become `tests/test_golden.py`.

### 9.1 Binance futures, 10x, 100 trades, $100 capital, fee $0.026/trade

| WR | netA | netB | netC | grossA | grossB | grossC | shA | shC |
|---|---|---|---|---|---|---|---|---|
| 20% | -2.60 | -4.46 | 53.40 | 0.0 | -1.94 | 56.0 | -0.013 | 0.113 |
| 40% | 97.40 | 156.01 | 289.40 | 100.0 | 162.69 | 292.0 | 0.398 | 0.501 |
| 50% | 147.40 | 319.08 | 407.40 | 150.0 | 329.96 | 410.0 | 0.590 | 0.691 |
| 60% | 197.40 | 586.01 | 525.40 | 200.0 | 603.73 | 528.0 | 0.806 | 0.909 |

B is `100 * (1.04^wins * 0.99^losses) - 100` for gross, with fee = `0.00026 * capital` per trade for net. **The HTML reports profit, not final value.** B net differs from HTML by < 0.5% purely due to win/loss path ordering for the fee; tests assert within tolerance 0.5%, not exact. A and C are exact.

### 9.2 Capital scaling (futures, WR 50%)

| Capital | aFixed | aPct | bPct | cFixed | cPct |
|---|---|---|---|---|---|
| $100 | 147.40 | 147.40 | 319.08 | 407.40 | 407.40 |
| $500 | 147.40 | 737.00 | 1595.38 | 407.40 | 2037.00 |
| $1000 | 147.40 | 1474.00 | 3190.77 | 407.40 | 4074.00 |

Fixed sizing is capital-independent; percentage sizing scales linearly. B scales linearly because both sizing and fee are proportional to capital.

### 9.3 fomo.family spot, flat $1.90 round-trip fee/trade

| WR | netA | netB | netC | grossA | grossC | shA (net) | shAg (gross) | shC (net) | shCg (gross) |
|---|---|---|---|---|---|---|---|---|---|
| 20% | -190.00 | -85.61 | -134.0 | 0.0 | 56.0 | -0.950 | 0.000 | -0.284 | 0.119 |
| 40% | -90.00 | -60.72 | 102.0 | 100.0 | 292.0 | -0.367 | 0.408 | 0.176 | 0.505 |
| 50% | -40.00 | -35.10 | 220.0 | 150.0 | 410.0 | -0.160 | 0.600 | 0.373 | 0.695 |
| 60% | 10.00 | 7.23 | 338.0 | 200.0 | 528.0 | 0.041 | 0.816 | 0.585 | 0.913 |

The $1.90 fee is `fee_spot($2 notional) = max(2*0.005, 0.95) * 2`, confirming the §5.4 formula reproduces the floor behaviour.

### 9.4 Fee fixtures

| Case | Expected |
|---|---|
| fomo round-trip, $2 position | $1.90 |
| fomo fee break-even position | $190 (0.5% == $0.95) |
| futures fee, $20 notional | $0.026 |
| 10x liquidation distance | -10% price |

## 10. Migration

1. `git mv` the 4 scripts + `trading-simulation/` into `legacy/`.
2. Optionally rewrite the 4 scripts as thin CLIs importing `core/` (`python -m legacy.future_value`). Decision deferred; `legacy/` is read-only reference by default.
3. Rewrite `README.md`: what the app is, how to run it, the module map, the formulas, a screenshot section.
4. `investment_details_20241118_130408.csv` and `csv/` stay as sample data for the DCA/portfolio CSV import (stretch goal, not in initial scope).

## 11. Risks and decisions

| Risk / decision | Resolution |
|---|---|
| Python 3.15 is very new | Verified cp315 wheels exist for fastapi, pydantic, uvicorn, pandas, numpy. No blocker. |
| `pandas` only needed if CSV import is built | Defer pandas; core math uses stdlib only. Keeps the dependency surface tiny. |
| Sharpe definition ambiguity | Pinned to per-trade, non-annualised, because that matches the HTML. Documented in §5.5. |
| Strategy B interpretation | Confirmed: compounding, profit reported net of initial capital, fee scales with capital. §5.6. |
| IDR vs USD | Both supported via formatter; default IDR. §7. |

## 12. Build order (feeds the implementation plan)

1. Project skeleton + `pyproject.toml` + venv.
2. `core/models.py` + `core/rates.py` + `core/dca.py` with golden tests.
3. `core/portfolio.py`, `core/fees.py`, `core/trading.py`, `core/sim.py` with golden tests.
4. `api/` endpoints + API tests.
5. `web/` shell, then one tab at a time (Invest -> Portfolio -> Trading -> Simulate).
6. Migration, README, final verification pass.
