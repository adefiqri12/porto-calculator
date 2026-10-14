# Porto Calculator

An offline calculator for investing and trading math: DCA, CAGR, portfolio
allocation, risk/reward, fees, leverage, and win-rate simulation. Runs in the
browser with a Python backend. No market data, no network calls, no accounts.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install fastapi "uvicorn[standard]" pydantic pytest httpx
.venv/bin/uvicorn api.app:create_app --factory --port 8000
```

Open <http://localhost:8000>. API docs are at <http://localhost:8000/docs>.

Run the tests:

```bash
.venv/bin/pytest -q
```

To check the UI end to end (real clicks on every tab, language toggle, and
console errors) against a running server:

```bash
.venv/bin/python tests/cdp_check.py
```

It defaults to `http://127.0.0.1:8000/`; override with `PORTO_URL`. It exits
non-zero on a missing card, an untranslated key, a failed restore, or any
console error.

## What it does

Four tabs, all live (change an input, results update):

| Tab | Inputs | Outputs |
|---|---|---|
| **Invest** | total return, years, monthly amount, annual ROI, months | CAGR, future value, total invested, total return, yearly table + chart |
| **Portfolio** | monthly amount, months, per-asset name/weight/ROI | per-asset and total future value, live weight-sum validation |
| **Trading** | preset, win rate, fee model, leverage, capital, trades | EV, break-even win rate, profit factor, Sharpe, net profit, liquidation warning |
| **Simulate** | win-rate range, capital, trades | A/B/C comparison table, capital scaling, best-by-Sharpe / best-by-net |

Currency (IDR/USD) and language (id/en) are togglable in the header. The
whole UI is translated, not just part of it: `web/i18n.js` holds the `id`/`en`
dictionary, static markup carries `data-i18n="key"` attributes, and generated
text calls `I18n.t()`. Indonesian and IDR are the defaults. `tests/test_i18n.py`
fails if any referenced key is missing from either language.

Inputs (and the language/currency choice) persist in `localStorage`, so the app
reopens where you left it. Nothing is sent to a server, and there is no account.
Persistence is best-effort: if storage is unavailable the calculator still works.

## Architecture

```
core/     pure Python math, standard library only, no web imports
api/      FastAPI + Pydantic, thin wrappers over core
web/      index.html + app.js + charts.js + i18n.js  (no build step, no CDN)
tests/    pytest, including golden fixtures
archive/  the original scripts and reports, kept for reference
docs/     design spec and implementation plan
```

Dependencies point one way: `web -> api -> core`. `core/` imports nothing from
the layers above it, which is what makes the math testable in isolation. That
invariant is enforced by `tests/test_core_is_pure.py`.

## Modules

| Module | Responsibility |
|---|---|
| `core/rates.py` | CAGR, annual-to-monthly conversion |
| `core/dca.py` | DCA future value, yearly breakdown |
| `core/portfolio.py` | allocation validation, per-asset future value |
| `core/presets.py` | strategy presets A / B / C / fomo |
| `core/fees.py` | futures and spot fee models, liquidation distance |
| `core/trading.py` | expected value, break-even WR, profit factor, per-trade Sharpe |
| `core/sim.py` | win-rate sweep, compounding equity, capital scaling |

## Formulas

```
CAGR              = (1 + total_return)^(1/years) - 1
monthly_rate      = annual_roi_pct / 100 / 12
DCA future value  = monthly * ((1 + r)^n - 1) / r * (1 + r)
EV per trade      = p * reward - (1 - p) * risk
break-even WR     = risk / (risk + reward)
profit factor     = (p * reward) / ((1 - p) * risk)
Sharpe per trade  = (EV - fee) / std            (NOT annualised)
futures fee       = notional * (0.05% * 2 + 0.03%)
spot fee          = max(notional * 0.5%, 0.95) * 2
liquidation (10x) = entry * (1 - 1/leverage)
```

Sharpe is deliberately **per-trade and not annualised**, which is what
reproduces the original reference reports.

## Verification

The original reports in `archive/trading-simulation/` contain hand-computed
tables. Those numbers are used as golden fixtures: `tests/test_golden.py`
re-derives them from the HTML source and asserts `core/` reproduces them. So
the port is proven against prior work rather than merely assumed correct.

Strategy B is path-dependent for fees (win/loss ordering affects the result),
so its net figures are asserted within a 0.5% tolerance. A and C are exact.

## Archive

`archive/` holds the four original CLI scripts, both HTML reports, and the
sample CSV data. They are superseded by `core/` and kept only as reference.
