"""KOSPI / KOSDAQ allocation signal: 5-month line + 60-day disparity overlay.

Pure data logic (no Streamlit) so it can be tested on its own.

Rule
----
1. Base weight from month-end closes (the last trading day's close of each
   month), compared with two simple averages of month-end closes that include
   the month itself:

       close >= 5-month avg and >= 10-month avg  -> green  -> 100% stocks
       close >= only one of them                 -> yellow ->  50% stocks
       close <  both                             -> red    ->   0% stocks

   A month's signal is fixed by its month-end close and holds for the whole
   next month.

2. Overlay: 60-day disparity = close / 60-day average close * 100.
   While it is >= DEV_THRESHOLD (120), cut the base weight one step
   (100% -> 50%, 50% -> 0%). It releases as soon as disparity drops back.

Data comes from Yahoo Finance's daily chart API. Long ranges are requested in
CHUNK_YEARS-year slices because Yahoo silently switches very long daily
requests to a coarser interval.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

KST = ZoneInfo("Asia/Seoul")

INDEXES = {
    "KOSPI": {"symbol": "^KS11", "label": "코스피", "start_year": 2004},
    "KOSDAQ": {"symbol": "^KQ11", "label": "코스닥", "start_year": 2001},
}

DEV_WINDOW = 60
DEV_THRESHOLD = 120.0
MA_SHORT_MONTHS = 5
MA_LONG_MONTHS = 10
CHUNK_YEARS = 4
TRADE_COST = 0.001  # 0.1% of the traded weight each time the weight changes

SIGNAL_WEIGHT = {"green": 1.0, "yellow": 0.5, "red": 0.0}
SIGNAL_LABEL = {"green": "초록불", "yellow": "노란불", "red": "빨간불"}
SIGNAL_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


# ── Data ───────────────────────────────────────────────────────────────────────
def kst_today() -> date:
    return datetime.now(KST).date()


def _fetch_chunk(symbol: str, start: datetime, end: datetime, session: requests.Session | None = None) -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}"
    params = {
        "period1": int(start.timestamp()),
        "period2": int(end.timestamp()),
        "interval": "1d",
        "events": "history",
    }
    getter = session.get if session is not None else requests.get
    response = getter(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    response.raise_for_status()
    result = (response.json().get("chart", {}).get("result") or [None])[0]
    if not result or not result.get("timestamp"):
        return pd.DataFrame(columns=["Date", "Close"])

    meta = result.get("meta", {})
    granularity = meta.get("dataGranularity")
    if granularity and granularity != "1d":
        raise ValueError(f"Yahoo returned {granularity} data for {symbol}; expected daily")

    offset = int(meta.get("gmtoffset") or 32400)
    timestamps = np.asarray(result["timestamp"], dtype="int64") + offset
    closes = (result.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    closes = list(closes) + [None] * max(0, len(timestamps) - len(closes))
    frame = pd.DataFrame({
        "Date": pd.to_datetime(timestamps, unit="s").normalize(),
        "Close": pd.to_numeric(pd.Series(closes[: len(timestamps)]), errors="coerce"),
    })
    return frame.dropna(subset=["Close"])


def fetch_daily_closes(symbol: str, start_year: int, now: datetime | None = None) -> pd.DataFrame:
    """Daily closes indexed by Korean trading date, oldest first."""
    now = now or datetime.now(timezone.utc)
    end_limit = now + timedelta(days=3)
    frames = []
    with requests.Session() as session:
        year = start_year
        while True:
            start = datetime(year, 1, 1, tzinfo=timezone.utc)
            if start > end_limit:
                break
            end = min(datetime(year + CHUNK_YEARS, 1, 1, tzinfo=timezone.utc), end_limit)
            frames.append(_fetch_chunk(symbol, start, end, session))
            year += CHUNK_YEARS
    if not frames:
        return pd.DataFrame(columns=["Date", "Close"])
    data = pd.concat(frames, ignore_index=True)
    return clean_daily(data)


def clean_daily(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["Date"] = pd.to_datetime(data["Date"]).dt.normalize()
    data["Close"] = pd.to_numeric(data["Close"], errors="coerce")
    data = data.dropna(subset=["Close"])
    data = data.drop_duplicates("Date", keep="last").sort_values("Date").reset_index(drop=True)
    return data


# ── Indicators ─────────────────────────────────────────────────────────────────
def add_disparity(daily: pd.DataFrame, window: int = DEV_WINDOW) -> pd.DataFrame:
    data = daily.copy()
    data["MA60"] = data["Close"].rolling(window, min_periods=window).mean()
    data["Disparity"] = data["Close"] / data["MA60"] * 100
    return data


def _classify(close: float, ma5: float, ma10: float) -> str | None:
    if pd.isna(ma5) or pd.isna(ma10):
        return None
    above5, above10 = close >= ma5, close >= ma10
    if above5 and above10:
        return "green"
    if above5 or above10:
        return "yellow"
    return "red"


def monthly_signals(daily: pd.DataFrame, today: date | None = None, min_periods: int | None = None) -> pd.DataFrame:
    """One row per confirmed month: month-end close, 5/10-month averages, signal.

    A month counts as confirmed once a later month has started in the data, or
    when today (KST) is already past it — so a morning run on the 1st still
    confirms the previous month even before the new month's first trade.

    min_periods=None requires full 5/10-month windows. min_periods=1 lets the
    first months use shorter windows (used only to reproduce earlier numbers).
    """
    today = today or kst_today()
    if daily.empty:
        return pd.DataFrame(columns=["Month", "Date", "Close", "MA5", "MA10", "Signal", "Weight"])

    data = daily[["Date", "Close"]].copy()
    data["Month"] = data["Date"].dt.to_period("M")
    month_ends = data.groupby("Month", sort=True).tail(1).reset_index(drop=True)

    current_month = pd.Period(today, freq="M")
    month_ends = month_ends[month_ends["Month"] < current_month].reset_index(drop=True)

    ma5_min = MA_SHORT_MONTHS if min_periods is None else min_periods
    ma10_min = MA_LONG_MONTHS if min_periods is None else min_periods
    month_ends["MA5"] = month_ends["Close"].rolling(MA_SHORT_MONTHS, min_periods=ma5_min).mean()
    month_ends["MA10"] = month_ends["Close"].rolling(MA_LONG_MONTHS, min_periods=ma10_min).mean()
    month_ends["Signal"] = [
        _classify(c, a, b) for c, a, b in zip(month_ends["Close"], month_ends["MA5"], month_ends["MA10"])
    ]
    month_ends["Weight"] = month_ends["Signal"].map(SIGNAL_WEIGHT)
    return month_ends[["Month", "Date", "Close", "MA5", "MA10", "Signal", "Weight"]]


def overlay_weight(base_weight: float, disparity: float | None, threshold: float | None = DEV_THRESHOLD) -> float:
    if threshold is None or disparity is None or pd.isna(disparity) or disparity < threshold:
        return base_weight
    return max(base_weight - 0.5, 0.0)


def disparity_trigger_price(daily: pd.DataFrame, threshold: float = DEV_THRESHOLD, window: int = DEV_WINDOW) -> float | None:
    """Close at which today's 60-day disparity would equal the threshold.

    With S = sum of the previous (window-1) closes and P today's close,
    P / ((S + P) / window) * 100 = threshold  ->  P = k*S / (window - k), k = threshold/100.
    """
    if len(daily) < window:
        return None
    prior_sum = float(daily["Close"].iloc[-(window - 1):].sum())
    k = threshold / 100.0
    return k * prior_sum / (window - k)


# ── Current status ─────────────────────────────────────────────────────────────
@dataclass
class IndexStatus:
    key: str
    label: str
    last_date: pd.Timestamp
    last_close: float
    confirmed_month: pd.Period
    confirmed_close: float
    ma5: float
    ma10: float
    signal: str
    base_weight: float
    disparity: float | None
    overlay_active: bool
    final_weight: float
    disparity_trigger: float | None
    green_above: float
    red_below: float
    live_signal: str
    just_confirmed: bool

    @property
    def nearest_boundary(self) -> tuple[str, float, float]:
        """(which, price, % move from last close) for the closest line to cross."""
        if self.live_signal == "red":
            return "노란불", self.red_below, (self.red_below / self.last_close - 1) * 100
        if self.live_signal == "green":
            return "노란불", self.green_above, (self.green_above / self.last_close - 1) * 100
        up = (self.green_above / self.last_close - 1) * 100
        down = (self.red_below / self.last_close - 1) * 100
        if abs(up) <= abs(down):
            return "초록불", self.green_above, up
        return "빨간불", self.red_below, down


def current_status(key: str, daily: pd.DataFrame, today: date | None = None) -> IndexStatus:
    today = today or kst_today()
    cfg = INDEXES[key]
    daily = add_disparity(daily)
    monthly = monthly_signals(daily, today).dropna(subset=["Signal"])
    if monthly.empty:
        raise ValueError(f"not enough monthly history for {key}")

    confirmed = monthly.iloc[-1]
    last = daily.iloc[-1]
    disparity = None if pd.isna(last["Disparity"]) else float(last["Disparity"])
    overlay_active = disparity is not None and disparity >= DEV_THRESHOLD
    base_weight = float(confirmed["Weight"])

    # Lines this month's close has to clear. With X = this month's close:
    #   X >= 5-month avg (incl. X)  <=>  X >= mean(previous 4 month-end closes)
    #   X >= 10-month avg (incl. X) <=>  X >= mean(previous 9 month-end closes)
    prev_closes = monthly["Close"]
    t5 = float(prev_closes.iloc[-(MA_SHORT_MONTHS - 1):].mean())
    t10 = float(prev_closes.iloc[-(MA_LONG_MONTHS - 1):].mean())
    green_above, red_below = max(t5, t10), min(t5, t10)
    last_close = float(last["Close"])
    if last_close >= green_above:
        live = "green"
    elif last_close >= red_below:
        live = "yellow"
    else:
        live = "red"

    last_period = last["Date"].to_period("M")
    just_confirmed = last_period < pd.Period(today, freq="M") and last_period == confirmed["Month"]

    return IndexStatus(
        key=key,
        label=cfg["label"],
        last_date=last["Date"],
        last_close=last_close,
        confirmed_month=confirmed["Month"],
        confirmed_close=float(confirmed["Close"]),
        ma5=float(confirmed["MA5"]),
        ma10=float(confirmed["MA10"]),
        signal=confirmed["Signal"],
        base_weight=base_weight,
        disparity=disparity,
        overlay_active=overlay_active,
        final_weight=overlay_weight(base_weight, disparity),
        disparity_trigger=disparity_trigger_price(daily),
        green_above=green_above,
        red_below=red_below,
        live_signal=live,
        just_confirmed=bool(just_confirmed),
    )


# ── Backtest ───────────────────────────────────────────────────────────────────
def daily_base_signal(daily: pd.DataFrame, monthly: pd.DataFrame) -> pd.Series:
    """Signal in force on each day: the latest month-end at or before that day."""
    sig = pd.Series(index=daily["Date"], dtype="object")
    sig.loc[monthly["Date"].values] = monthly["Signal"].values
    return sig.ffill().reset_index(drop=True)


def run_backtest(
    daily: pd.DataFrame,
    dev_threshold: float | None = DEV_THRESHOLD,
    today: date | None = None,
    min_periods: int | None = None,
    trade_cost: float = TRADE_COST,
) -> dict:
    """Close-to-close simulation. The weight decided at day t-1's close
    (month signal in force + that day's disparity) earns day t's return.
    Cash earns nothing. Price index only (no dividends)."""
    data = add_disparity(daily).reset_index(drop=True)
    # Treat every completed month in the data as confirmed for history.
    last_date = data["Date"].iloc[-1]
    horizon = (last_date + pd.offsets.MonthBegin(1)).date()
    monthly = monthly_signals(data, today or horizon, min_periods=min_periods).dropna(subset=["Signal"])
    base_sig = daily_base_signal(data, monthly)

    valid = data["Disparity"].notna() & base_sig.notna()
    if not valid.any():
        raise ValueError("not enough history to backtest")
    start = int(np.argmax(valid.values))

    closes = data["Close"].to_numpy()
    disp = data["Disparity"].to_numpy()
    base_w = base_sig.map(SIGNAL_WEIGHT).to_numpy(dtype="float64")

    n = len(data)
    weights = np.full(n, np.nan)
    nav_sys = np.full(n, np.nan)
    nav_hold = np.full(n, np.nan)
    nav_sys[start] = nav_hold[start] = 1.0
    prev_w = base_w[start]
    weights[start] = prev_w
    for t in range(start + 1, n):
        ret = closes[t] / closes[t - 1] - 1
        d = disp[t - 1]
        w = base_w[t - 1]
        if dev_threshold is not None and not np.isnan(d) and d >= dev_threshold:
            w = max(w - 0.5, 0.0)
        cost = abs(w - prev_w) * trade_cost
        nav_sys[t] = nav_sys[t - 1] * (1 + w * ret - cost)
        nav_hold[t] = nav_hold[t - 1] * (1 + ret)
        weights[t - 1] = w
        prev_w = w
    weights[n - 1] = overlay_weight(base_w[n - 1], disp[n - 1], dev_threshold)

    curve = pd.DataFrame({
        "Date": data["Date"],
        "Close": data["Close"],
        "Weight": weights,
        "System": nav_sys,
        "Hold": nav_hold,
    }).iloc[start:].reset_index(drop=True)

    years = (curve["Date"].iloc[-1] - curve["Date"].iloc[0]).days / 365.25
    return {
        "curve": curve,
        "start": curve["Date"].iloc[0],
        "end": curve["Date"].iloc[-1],
        "years": years,
        "system": _stats(curve["System"], years),
        "hold": _stats(curve["Hold"], years),
        "trades": int((curve["Weight"].diff().abs() > 1e-9).sum()),
    }


def _stats(nav: pd.Series, years: float) -> dict:
    final = float(nav.iloc[-1])
    mdd = float((nav / nav.cummax() - 1).min())
    cagr = final ** (1 / years) - 1 if years > 0 and final > 0 else float("nan")
    return {"total": final - 1, "cagr": cagr, "mdd": mdd}
