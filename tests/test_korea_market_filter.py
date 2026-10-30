"""Market filter: a stock never holds more than its market's weight. Run: python tests/test_korea_market_filter.py"""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import korea_signal_engine as eng  # noqa: E402


def rising(years: int = 6, start: str = "2018-01-02", step: float = 1.0008) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=years * 252)
    return pd.DataFrame({"Date": dates, "Close": 100 * step ** np.arange(len(dates))})


def status(final_weight=1.0, base_weight=1.0, live="green", key="X", label="X") -> eng.IndexStatus:
    return eng.IndexStatus(key=key, label=label, last_date=pd.Timestamp("2026-10-30"), last_close=100.0,
                           confirmed_month=pd.Period("2026-09"), confirmed_close=100.0, ma5=90.0, ma10=80.0,
                           signal="green", base_weight=base_weight, disparity=100.0, overlay_active=False,
                           final_weight=final_weight, disparity_trigger=None, green_above=95.0, red_below=85.0,
                           live_signal=live, just_confirmed=False)


def test_gate_of_zero_keeps_the_stock_in_cash():
    daily = rising()
    free = eng.run_backtest(daily)
    shut = eng.run_backtest(daily, market_gate=pd.Series(0.0, index=daily["Date"]))
    assert free["system"]["total"] > 0.5                    # a steady riser is held without the gate
    assert abs(shut["system"]["total"]) < 1e-9              # never in the market -> no return, no cost
    assert shut["trades"] == 0


def test_gate_of_one_changes_nothing():
    daily = rising()
    free = eng.run_backtest(daily)
    full = eng.run_backtest(daily, market_gate=pd.Series(1.0, index=daily["Date"]))
    assert np.isclose(free["system"]["total"], full["system"]["total"])
    assert free["trades"] == full["trades"]


def test_gate_caps_exposure_at_half():
    daily = rising()
    half = eng.run_backtest(daily, market_gate=pd.Series(0.5, index=daily["Date"]))
    assert half["curve"]["Weight"].max() <= 0.5 + 1e-12


def test_gate_series_follows_the_index_signal():
    gate = eng.index_gate_series(rising())
    assert gate.dropna().isin([0.0, 0.5, 1.0]).all()
    assert gate.iloc[-1] == 1.0                              # a steady riser ends in the 100% zone
    assert gate.iloc[:100].isna().all()                      # no signal before 10 month-ends exist


def test_cap_to_market():
    stock, market = status(final_weight=1.0), status(base_weight=0.5, label="코스피")
    capped = eng.cap_to_market(stock, market)
    assert capped.final_weight == 0.5 and capped.uncapped_weight == 1.0
    assert capped.market_label == "코스피" and capped.market_weight == 0.5
    assert stock.final_weight == 1.0                         # the original is untouched
    low = eng.cap_to_market(status(final_weight=0.0), status(base_weight=1.0))
    assert low.final_weight == 0.0                           # a cap never raises a weight


def test_capped_next_weight():
    assert eng.capped_next_weight(status(live="green"), status(live="red")) == 0.0
    assert eng.capped_next_weight(status(live="green"), status(live="yellow")) == 0.5
    assert eng.capped_next_weight(status(live="yellow"), status(live="green")) == 0.5


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
