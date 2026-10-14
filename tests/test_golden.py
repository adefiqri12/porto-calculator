"""Independent verification of core/ against the archived reference reports.

This file deliberately re-derives every expectation from the JS data arrays in
archive/trading-simulation/*.html rather than restating numbers by hand. If a
number is wrong here, it is wrong in the original report too.

Reference: archive/trading-simulation/binance-futures.html (futures, 10x)
           archive/trading-simulation/meme-coin.html        (fomo spot)

Model constants, all read off the reports:
  futures: 100 trades, $100 capital, taker 0.05%/side + 0.03% funding
  fomo:    100 trades, $2 position, round-trip fee $1.90
  strategy A: reward 4.0, risk 1.0   (RR 4:1)
  strategy B: compounding, x1.04 win / x0.99 loss
  strategy C: reward 10.0, risk 1.8  (RR 5.56:1)
"""
import pathlib
import re

import pytest

from core.fees import futures_fee, spot_fee
from core.sim import (
    FIXED_FEE_PER_TRADE,
    capital_scaling,
    compound_equity,
    fixed_profit,
    percent_profit,
    sweep_win_rates,
)
from core.trading import sharpe_per_trade

ARCHIVE = pathlib.Path("archive/trading-simulation")
BINANCE = ARCHIVE / "binance-futures.html"
MEME = ARCHIVE / "meme-coin.html"

TRADES = 100
CAPITAL = 100.0
A = {"reward": 4.0, "risk": 1.0}
C = {"reward": 10.0, "risk": 1.8}

_ROW = re.compile(r"\{([^}]*)\}")


def parse_rows(path, marker):
    """Pull `{key:value, ...}` rows out of an HTML file that contain `marker:`."""
    rows = []
    for match in _ROW.finditer(path.read_text()):
        body = match.group(1)
        if f"{marker}:" not in body:
            continue
        row = {}
        for part in body.split(","):
            if ":" not in part:
                continue
            key, _, value = part.partition(":")
            key, value = key.strip(), value.strip()
            try:
                row[key] = float(value)
            except ValueError:
                row[key] = value
        rows.append(row)
    return rows


BINANCE_WR = parse_rows(BINANCE, "wr")
BINANCE_CAP = parse_rows(BINANCE, "cap")
MEME_WR = parse_rows(MEME, "wr")


def test_reports_were_actually_parsed():
    # Guard: if the HTML moves or the regex breaks, fail loudly instead of
    # silently passing on an empty list.
    assert len(BINANCE_WR) == 7, BINANCE_WR
    assert len(BINANCE_CAP) == 3, BINANCE_CAP
    assert len(MEME_WR) == 7, MEME_WR
    assert BINANCE_WR[0]["wr"] == 20.0
    assert BINANCE_CAP[0]["cap"] == 100.0


# ---------------------------------------------------------------- futures

@pytest.mark.parametrize("row", BINANCE_WR, ids=lambda r: f"wr{int(r['wr'])}")
def test_futures_strategy_a_matches_report(row):
    wr = row["wr"]
    p = wr / 100.0
    from core.trading import expected_value

    assert fixed_profit("A", wr, TRADES) == pytest.approx(row["netA"], abs=0.01)
    assert TRADES * expected_value(p, A["reward"], A["risk"]) == pytest.approx(row["grossA"], abs=0.01)
    assert sharpe_per_trade(p, A["reward"], A["risk"], FIXED_FEE_PER_TRADE) == pytest.approx(
        row["shA"], abs=1e-3
    )


@pytest.mark.parametrize("row", BINANCE_WR, ids=lambda r: f"wr{int(r['wr'])}")
def test_futures_strategy_c_matches_report(row):
    wr = row["wr"]
    p = wr / 100.0
    from core.trading import expected_value

    assert fixed_profit("C", wr, TRADES) == pytest.approx(row["netC"], abs=0.01)
    assert TRADES * expected_value(p, C["reward"], C["risk"]) == pytest.approx(row["grossC"], abs=0.01)
    assert sharpe_per_trade(p, C["reward"], C["risk"], FIXED_FEE_PER_TRADE) == pytest.approx(
        row["shC"], abs=1e-3
    )


@pytest.mark.parametrize("row", BINANCE_WR, ids=lambda r: f"wr{int(r['wr'])}")
def test_futures_strategy_b_gross_matches_report_exactly(row):
    # No fee -> the win/loss ordering is irrelevant, so this is exact.
    gross = compound_equity(CAPITAL, row["wr"], TRADES, fee_rate=0.0) - CAPITAL
    assert gross == pytest.approx(row["grossB"], abs=0.01)


@pytest.mark.parametrize("row", BINANCE_WR, ids=lambda r: f"wr{int(r['wr'])}")
def test_futures_strategy_b_net_matches_report_within_tolerance(row):
    # Fee accrues on the changing equity, so the result depends on the order in
    # which wins and losses fall. The report used a particular ordering; we use a
    # deterministic interleave. Agreement is within a fraction of a percent.
    net = compound_equity(CAPITAL, row["wr"], TRADES) - CAPITAL
    assert net == pytest.approx(row["netB"], rel=0.005)


@pytest.mark.parametrize("row", BINANCE_CAP, ids=lambda r: f"cap{int(r['cap'])}")
def test_futures_capital_scaling_matches_report(row):
    cap = row["cap"]
    at_wr = 50.0

    assert fixed_profit("A", at_wr, TRADES) == pytest.approx(row["aFixed"], abs=0.01)
    assert fixed_profit("C", at_wr, TRADES) == pytest.approx(row["cFixed"], abs=0.01)
    assert percent_profit("A", cap, at_wr, TRADES) == pytest.approx(row["aPct"], abs=0.01)
    assert percent_profit("C", cap, at_wr, TRADES) == pytest.approx(row["cPct"], abs=0.01)
    assert compound_equity(cap, at_wr, TRADES) - cap == pytest.approx(row["bPct"], rel=0.005)


def test_futures_report_capital_rows_are_consistent_with_wr50():
    # The capital table is stated at 50% win rate; confirm that assumption holds.
    assert BINANCE_CAP[0]["aFixed"] == pytest.approx(
        next(r["netA"] for r in BINANCE_WR if r["wr"] == 50.0), abs=0.01
    )


# ------------------------------------------------------------------- fomo

def test_fomo_fee_is_one_ninety_round_trip():
    assert spot_fee(2.0) == pytest.approx(1.90)
    assert futures_fee(20.0) == pytest.approx(0.026)


@pytest.mark.parametrize("row", MEME_WR, ids=lambda r: f"wr{int(r['wr'])}")
def test_fomo_matches_report(row):
    wr = row["wr"]
    p = wr / 100.0
    from core.trading import expected_value

    fee = spot_fee(2.0)  # $1.90 per trade
    gross_a = TRADES * expected_value(p, A["reward"], A["risk"])
    gross_c = TRADES * expected_value(p, C["reward"], C["risk"])

    assert gross_a == pytest.approx(row["grossA"], abs=0.01)
    assert gross_c == pytest.approx(row["grossC"], abs=0.01)
    assert gross_a - TRADES * fee == pytest.approx(row["netA"], abs=0.01)
    assert gross_c - TRADES * fee == pytest.approx(row["netC"], abs=0.01)

    # net Sharpe deducts the fee, gross Sharpe does not
    assert sharpe_per_trade(p, A["reward"], A["risk"], fee) == pytest.approx(row["shA"], abs=1e-3)
    assert sharpe_per_trade(p, A["reward"], A["risk"], 0.0) == pytest.approx(row["shAg"], abs=1e-3)
    assert sharpe_per_trade(p, C["reward"], C["risk"], fee) == pytest.approx(row["shC"], abs=1e-3)
    assert sharpe_per_trade(p, C["reward"], C["risk"], 0.0) == pytest.approx(row["shCg"], abs=1e-3)


def test_fomo_net_equals_gross_minus_fee_on_every_row():
    # Structural check independent of the formulas: the report's net and gross
    # columns must differ by exactly 100 trades x $1.90.
    for row in MEME_WR:
        assert row["grossA"] - row["netA"] == pytest.approx(190.0, abs=0.01)
        assert row["grossC"] - row["netC"] == pytest.approx(190.0, abs=0.01)


# ------------------------------------------------------- cross-report check

def test_sweep_helper_agrees_with_report_rows():
    # sweep_win_rates is what the API actually serves; check it end to end.
    wrs = [r["wr"] for r in BINANCE_WR]
    rows = {r["wr"]: r for r in sweep_win_rates("A", wrs, CAPITAL, TRADES)}
    for expected in BINANCE_WR:
        got = rows[expected["wr"]]
        assert got["net_a"] == pytest.approx(expected["netA"], abs=0.01)
        assert got["net_c"] == pytest.approx(expected["netC"], abs=0.01)
        assert got["gross_a"] == pytest.approx(expected["grossA"], abs=0.01)
        assert got["sh_a"] == pytest.approx(expected["shA"], abs=1e-3)
        assert got["sh_c"] == pytest.approx(expected["shC"], abs=1e-3)


def test_capital_scaling_helper_agrees_with_report_rows():
    rows = {r["capital"]: r for r in capital_scaling("A", [100.0, 500.0, 1000.0], 50.0, TRADES)}
    for expected in BINANCE_CAP:
        got = rows[expected["cap"]]
        assert got["fixed_value"] == pytest.approx(expected["aFixed"], abs=0.01)
        assert got["percent_value"] == pytest.approx(expected["aPct"], abs=0.01)
        assert got["compounding_value"] == pytest.approx(expected["bPct"], rel=0.005)
