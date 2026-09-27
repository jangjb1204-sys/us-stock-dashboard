"""Korea Market Signals — KOSPI / KOSDAQ stock-vs-cash allocation.

Opened from main.py with ?dashboard=korea. The rule and all numbers live in
korea_signal_engine.py; this file only fetches (cached) and draws.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import korea_signal_engine as engine
import ui_theme as ui

CACHE_TTL_SECONDS = 60 * 60 * 3
LISTING_PATH = Path(__file__).resolve().parent / "korea_stock_list.csv"
ETF_LIST_PATH = Path(__file__).resolve().parent / "korea_etf_list.csv"

# Allocation levels as greys (Tesla-style monochrome): brighter = more stock.
SIGNAL_COLOR = {"green": ui.LEVEL_FULL, "yellow": ui.LEVEL_HALF, "red": ui.LEVEL_NONE}
# Validated pair on the chart surface (dataviz validator): blue + neutral grey
# stay apart in normal and color-blind vision; the old blue/violet pair did not.
# Same muted blue / amber as the US chart's MA20 / MA60, so the 10-month line
# no longer looks like the grey month-end threshold lines.
CLOSE_COLOR, MA5_COLOR, MA10_COLOR = ui.TEXT, "#4C8DF0", "#BA852B"
PLOT_CONFIG = {"displayModeBar": False, "responsive": True, "scrollZoom": False, "doubleClick": False}

# Page-only pieces; everything else comes from ui_theme.BASE_CSS.
PAGE_CSS = ui.html(f"""
<style>
.kr-panels {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); column-gap:44px; row-gap:22px; margin:0 0 .4rem; }}
.kr-panels.single {{ grid-template-columns:minmax(0,1fr); max-width:560px; }}
.kr-panel {{ padding-top:22px; border-top:1px solid {ui.LINE}; min-width:0; }}
.kr-panel .top {{ display:flex; justify-content:space-between; gap:12px; color:{ui.MUTED}; font-size:12px; font-weight:560; text-transform:uppercase; letter-spacing:.04em; }}
.kr-panel .weight {{ margin-top:.55rem; font-variant-numeric:tabular-nums; font-size:48px; font-weight:650; letter-spacing:-0.026em; line-height:1; color:{ui.TEXT}; }}
.kr-panel .weight small {{ margin-left:10px; font-size:.95rem; font-weight:500; letter-spacing:0; color:rgba(255,255,255,.56); }}
.kr-panel {{ transition: border-color .15s ease; }}
.kr-panel:not(.sel) .weight, .kr-panel:not(.sel) .meta {{ opacity:.45; }}
.kr-panel.sel {{ border-top-color:rgba(242,245,248,.85); }}
div[data-testid="stColumn"]:has([class*="st-key-kr_card_"]) {{ position:relative; }}
div[data-testid="stColumn"]:has([class*="st-key-kr_card_"]):hover .kr-panel:not(.sel) .weight,
div[data-testid="stColumn"]:has([class*="st-key-kr_card_"]):hover .kr-panel:not(.sel) .meta {{ opacity:.75; }}
[class*="st-key-kr_card_"] {{ position:absolute!important; inset:0; width:100%!important; height:100%!important; z-index:3; margin:0!important; }}
[class*="st-key-kr_card_"] button {{ width:100%!important; height:100%!important; opacity:0; cursor:pointer; }}
.kr-panel .meta {{ margin-top:.8rem; color:rgba(255,255,255,.5); font-size:.84rem; }}
.kr-panel .meta b {{ color:{ui.TEXT}; font-weight:600; }}
.kr-level {{ display:inline-flex; align-items:center; gap:7px; font-variant-numeric:tabular-nums; }}
.kr-level i {{ width:8px; height:8px; border-radius:2px; display:inline-block; }}
.kr-sentence {{ margin:1.3rem 0 1.6rem; color:rgba(255,255,255,.72); font-size:.92rem; line-height:1.65; }}
.kr-sentence b {{ color:{ui.TEXT}; }}
.kr-rule {{ color:rgba(255,255,255,.72); font-size:.88rem; line-height:1.7; }}
.kr-rule b {{ color:{ui.TEXT}; }}
.kr-zone {{ margin:1.8rem 0 1.9rem; }}
.kr-zone-head {{ display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; color:{ui.MUTED}; font-size:12px; font-weight:560; letter-spacing:.03em; margin-bottom:.7rem; }}
.kr-zone-head b {{ color:{ui.TEXT}; font-size:.95rem; font-variant-numeric:tabular-nums; }}
.kr-bar {{ position:relative; display:grid; grid-template-columns:1fr 2fr 1fr; gap:3px; height:30px; }}
.kr-bar .seg {{ display:flex; align-items:center; justify-content:center; border-radius:6px; font-size:.78rem; font-weight:600;
    color:rgba(255,255,255,.40); background:rgba(255,255,255,.045); font-variant-numeric:tabular-nums; }}
.kr-bar .seg.on {{ background:rgba(255,255,255,.16); color:{ui.TEXT}; }}
.kr-marker {{ position:absolute; top:-6px; bottom:-6px; width:3px; margin-left:-1.5px; border-radius:2px; background:{ui.TEXT}; box-shadow:0 0 0 2px {ui.BG}; }}
.kr-ticks {{ position:relative; height:1.4rem; margin-top:.35rem; font-variant-numeric:tabular-nums; font-size:.8rem; color:rgba(255,255,255,.62); }}
.kr-ticks span {{ position:absolute; transform:translateX(-50%); white-space:nowrap; }}
.kr-zone-foot {{ margin-top:.35rem; color:rgba(255,255,255,.5); font-size:.8rem; }}
.kr-zone-foot b {{ color:{ui.TEXT}; font-weight:600; }}
@media (max-width:640px) {{ .kr-panels {{ grid-template-columns:1fr; }} .kr-panel .weight {{ font-size:40px; }} }}
</style>
""")

# ── Data (cached) ──────────────────────────────────────────────────────────────
# day_key (the KST date) is part of every cache key so each new day refetches.
@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def load_history(symbol: str, start_year: int, day_key: str) -> tuple[pd.DataFrame, dict]:
    return engine.fetch_history(symbol, start_year)


def load_daily(key: str, day_key: str) -> pd.DataFrame:
    cfg = engine.INDEXES[key]
    return load_history(cfg["symbol"], cfg["start_year"], day_key)[0]


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_listing(day_key: str) -> tuple[pd.DataFrame, bool]:
    """Every KOSPI/KOSDAQ company (KRX KIND) and every Korean ETF (Naver), as
    (listing, both_live). Each half falls back to the copy shipped in the repo
    when its source can't be reached."""
    live = True
    try:
        companies = engine.fetch_krx_listing()
    except Exception:
        companies, live = engine.load_listing_csv(LISTING_PATH), False
    try:
        etfs = engine.fetch_etf_listing()
    except Exception:
        etfs, live = engine.load_listing_csv(ETF_LIST_PATH), False
    return pd.concat([companies, etfs], ignore_index=True).drop_duplicates("code"), live


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_etf_search(query_key: str, query: str, day_key: str) -> pd.DataFrame:
    """Korean ETFs matching the query on Yahoo's symbol search (empty on failure)."""
    try:
        return engine.search_yahoo_etfs(query)
    except Exception:
        return pd.DataFrame(columns=engine.LISTING_COLUMNS)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def load_stock(code: str, market: str, day_key: str) -> dict | None:
    """First Yahoo symbol for this KRX code that has data, or None."""
    for symbol in engine.yahoo_candidates(code, market or None):
        try:
            daily, meta = load_history(symbol, engine.STOCK_START_YEAR, day_key)
        except engine.SymbolNotFound:
            continue
        if not daily.empty:
            return {"symbol": symbol, "daily": daily,
                    "yahoo_name": meta.get("shortName") or meta.get("longName") or code}
    return None


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def load_backtests(symbol: str, start_year: int, day_key: str) -> dict:
    daily = load_history(symbol, start_year, day_key)[0]
    return {
        "overlay": engine.run_backtest(daily, engine.DEV_THRESHOLD),
        "base": engine.run_backtest(daily, None),
    }


# ── Formatting helpers ─────────────────────────────────────────────────────────
def fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.{digits}f}"


def fmt_pct(value: float | None, digits: int = 1, sign: bool = True) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:+.{digits}f}%" if sign else f"{value:.{digits}f}%"


def price_digits(key: str) -> int:
    """Index levels keep two decimals; stock prices are whole won."""
    return 2 if key in engine.INDEXES else 0


def weight_text(weight: float) -> str:
    return f"{int(round(weight * 100))}%"


def level_name(signal: str) -> str:
    """A signal is named by what it means: the stock weight."""
    return f"주식 {weight_text(engine.SIGNAL_WEIGHT[signal])}"


def signal_chip(signal: str, prefix: str = "") -> str:
    return (f"<span class='kr-level'><i style='background:{SIGNAL_COLOR[signal]}'></i>"
            f"{escape(prefix)}{weight_text(engine.SIGNAL_WEIGHT[signal])}</span>")


def month_label(period: pd.Period) -> str:
    return f"{period.month}월"


def is_last_weekday_of_month(day: date) -> bool:
    if day.weekday() >= 5:
        return False
    nxt = day + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt.month != day.month


def closed_weekdays_text(last_date, today: date) -> str:
    """Weekdays between the last close and today with no data — market
    holidays (e.g. Chuseok) — as '9/24~9/25 휴장', or ''."""
    last = pd.Timestamp(last_date).date()
    gap, cur = [], last + timedelta(days=1)
    while cur < today:
        if cur.weekday() < 5:
            gap.append(cur)
        cur += timedelta(days=1)
    if not gap:
        return ""
    span = f"{gap[0].month}/{gap[0].day}" + (f"~{gap[-1].month}/{gap[-1].day}" if len(gap) > 1 else "")
    return f"{span} 휴장"


def weekdays_left_in_month(day: date) -> int:
    count, cur = 0, day
    while cur.month == day.month:
        if cur.weekday() < 5:
            count += 1
        cur += timedelta(days=1)
    return count


# ── Charts ─────────────────────────────────────────────────────────────────────
def _style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 36, "b": 24},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1, "font": {"size": 11}},
        hovermode="x unified",
        dragmode=False,
        **ui.PLOT_LAYOUT,
    )
    fig.update_xaxes(fixedrange=True, tickfont={"color": "rgba(245,245,247,0.54)", "size": 10}, **ui.X_GRID)
    fig.update_yaxes(fixedrange=True, tickfont={"color": "rgba(245,245,247,0.46)", "size": 10}, **ui.Y_GRID)
    return fig


def signal_runs(data: pd.DataFrame) -> list[dict]:
    """Consecutive months with the same signal, merged: {sig, start, end, months}."""
    runs: list[dict] = []
    for month, sig in zip(data["Month"], data["Signal"]):
        start = month.to_timestamp(how="start")
        end = month.to_timestamp(how="end").normalize() + pd.Timedelta(days=1)
        if runs and runs[-1]["sig"] == sig:
            runs[-1]["end"], runs[-1]["months"] = end, runs[-1]["months"] + 1
        else:
            runs.append({"sig": sig, "start": start, "end": end, "months": 1})
    return runs


def build_monthly_chart(monthly: pd.DataFrame, status: engine.IndexStatus, years: int = 6, digits: int = 2) -> go.Figure:
    """Month-end close with its 5/10-month averages, and each month's signal as
    a thin ribbon under the chart (runs of the same signal drawn as one
    segment). This month: the latest close as one dot, plus the two closing
    lines it has to clear."""
    yfmt = f"%{{y:,.{digits}f}}"
    cutoff = status.confirmed_month - 12 * years
    data = monthly[monthly["Month"] >= cutoff].copy()
    x = data["Month"].dt.to_timestamp(how="end").dt.normalize()
    month_start = status.last_date.to_period("M").to_timestamp(how="start")
    month_end = (status.last_date + pd.offsets.MonthEnd(0)).normalize()
    last_confirmed_x = x.iloc[-1]
    sig_text = data["Signal"].map(lambda sgn: f"다음 달 {level_name(sgn)}")
    live_color = ui.TEXT

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.95, 0.05], vertical_spacing=0.025)
    seg_end = month_end + pd.Timedelta(days=25)  # a little room so this month's lines read as lines
    line = lambda color: {"color": color, "width": 2, "shape": "linear"}
    fig.add_trace(go.Scatter(x=x, y=data["Close"], name="월말 종가", mode="lines", line=line(CLOSE_COLOR),
                             customdata=sig_text,
                             hovertemplate="월말 종가 " + yfmt + "<br>%{customdata}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=data["MA5"], name="5개월선", mode="lines", line=line(MA5_COLOR),
                             hovertemplate="5개월선 " + yfmt + "<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=data["MA10"], name="10개월선", mode="lines", line=line(MA10_COLOR),
                             hovertemplate="10개월선 " + yfmt + "<extra></extra>"), row=1, col=1)

    # This month so far: a faint link from last month-end, one dot for the latest close.
    fig.add_trace(go.Scatter(x=[last_confirmed_x, status.last_date], y=[data["Close"].iloc[-1], status.last_close],
                             mode="lines", line={"color": "rgba(242,245,248,0.38)", "width": 2, "dash": "dot"},
                             hoverinfo="skip", showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=[status.last_date], y=[status.last_close], mode="markers", name="이번 달 최근 종가",
                             marker={"size": 11, "color": live_color, "line": {"width": 2, "color": ui.PLOT_BG}},
                             hovertemplate="이번 달 최근 종가 " + yfmt + "<extra></extra>", showlegend=False), row=1, col=1)
    # The two lines this month's close has to clear, only across this month.
    # No text in the chart: the prices are in the stat row right above it, and
    # labels in a side margin got cut off on phones. Hover shows them.
    for level, color, text in ((status.green_above, ui.TEXT, f"이달 말 100% 기준 ≥ {status.green_above:,.{digits}f}"),
                               (status.red_below, "rgba(242,245,248,0.55)", f"이달 말 0% 기준 < {status.red_below:,.{digits}f}")):
        fig.add_trace(go.Scatter(x=[last_confirmed_x, seg_end], y=[level, level], mode="lines",
                                 line={"color": color, "width": 2, "dash": "dot"}, name=text, hovertemplate=text + "<extra></extra>",
                                 showlegend=False), row=1, col=1)

    # Signal ribbon: one continuous segment per run, a 2-day gap between runs;
    # this month's in-progress segment faded.
    for run in signal_runs(data):
        span = run["end"] - run["start"]
        fig.add_trace(go.Bar(
            x=[run["start"] + span / 2], y=[1], width=[(span - pd.Timedelta(days=2)).total_seconds() * 1000],
            marker={"color": SIGNAL_COLOR[run["sig"]], "line": {"width": 0}},
            hovertemplate=f"{level_name(run['sig'])} · {run['months']}개월<extra></extra>",
            showlegend=False,
        ), row=2, col=1)
    span = month_end + pd.Timedelta(days=1) - month_start
    fig.add_trace(go.Bar(
        x=[month_start + span / 2], y=[1], width=[(span - pd.Timedelta(days=2)).total_seconds() * 1000],
        marker={"color": SIGNAL_COLOR[status.live_signal], "opacity": 0.35, "line": {"width": 0}},
        hovertemplate="이번 달 진행 중<extra></extra>", showlegend=False,
    ), row=2, col=1)

    _style(fig, 460)
    fig.update_layout(bargap=0, margin={"l": 10, "r": 12, "t": 36, "b": 24})
    # Log scale: a 10% move is the same height in 2021 and in 2026, so older
    # crossings aren't flattened by the recent rally.
    fig.update_yaxes(type="log", tickformat=",.0f", nticks=6, row=1, col=1)
    fig.update_yaxes(visible=False, range=[0, 1], showgrid=False, row=2, col=1)
    fig.update_xaxes(showgrid=False, row=2, col=1)
    fig.update_xaxes(tickformat="%y.%m", range=[x.iloc[0] - pd.Timedelta(days=35), seg_end + pd.Timedelta(days=5)])
    return fig


def signal_key_html() -> str:
    """One-line key for the signal ribbon, as page text so it wraps on phones."""
    swatch = lambda sig: (f"<span style='display:inline-block;width:10px;height:10px;border-radius:2px;"
                          f"background:{SIGNAL_COLOR[sig]};margin:0 5px 0 10px;vertical-align:-1px'></span>")
    items = "".join(f"{swatch(sig)}{weight_text(engine.SIGNAL_WEIGHT[sig])}" for sig in ("green", "yellow", "red"))
    return f"<div class='tj-caption' style='margin-top:-.2rem'>월별 주식 비중{items} · 오른쪽 점선 = 이달 말 100%·0% 기준가 · 로그 눈금</div>"


def build_disparity_chart(daily: pd.DataFrame, years: int = 3, digits: int = 2) -> go.Figure:
    yfmt = f"%{{y:,.{digits}f}}"
    data = engine.add_disparity(daily)
    data = data[data["Date"] >= data["Date"].iloc[-1] - pd.DateOffset(years=years)]
    hot = data[data["Disparity"] >= engine.DEV_THRESHOLD]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.62, 0.38], vertical_spacing=0.05)
    fig.add_trace(go.Scatter(x=data["Date"], y=data["Close"], name="종가", mode="lines",
                             line={"color": "#f5f5f7", "width": 1.8},
                             hovertemplate="%{x|%Y-%m-%d}<br>종가 " + yfmt + "<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data["Date"], y=data["MA60"], name="60일 평균", mode="lines",
                             line={"color": MA10_COLOR, "width": 1.3, "dash": "dot"},
                             hovertemplate="60일 평균 " + yfmt + "<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=hot["Date"], y=hot["Close"], name=f"이격도 {engine.DEV_THRESHOLD:.0f}↑ (과열)",
                             mode="markers", marker={"size": 5, "color": MA5_COLOR},
                             hovertemplate="과열 " + yfmt + "<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data["Date"], y=data["Disparity"], name="60일 이격도", mode="lines",
                             line={"color": MA5_COLOR, "width": 1.6},
                             hovertemplate="이격도 %{y:.1f}<extra></extra>"), row=2, col=1)
    fig.add_hline(y=engine.DEV_THRESHOLD, line={"color": "rgba(255,255,255,0.55)", "width": 1, "dash": "dash"}, row=2, col=1)
    fig.add_hline(y=100, line={"color": "rgba(255,255,255,0.25)", "width": 1}, row=2, col=1)
    _style(fig, 500)
    fig.update_xaxes(tickformat="%y.%m")
    return fig


def build_backtest_chart(backtests: dict) -> go.Figure:
    over = backtests["overlay"]["curve"]
    base = backtests["base"]["curve"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.05)
    fig.add_trace(go.Scatter(x=over["Date"], y=over["Hold"], name="그냥 보유", mode="lines",
                             line={"color": "rgba(245,245,247,0.45)", "width": 1.4},
                             hovertemplate="그냥 보유 %{y:.2f}배<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=base["Date"], y=base["System"], name="5개월선만", mode="lines",
                             line={"color": MA5_COLOR, "width": 1.5},
                             hovertemplate="5개월선만 %{y:.2f}배<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=over["Date"], y=over["System"], name=f"5개월선 + 이격도{engine.DEV_THRESHOLD:.0f}",
                             mode="lines", line={"color": ui.TEXT, "width": 2},
                             hovertemplate="5개월선+이격도 %{y:.2f}배<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=over["Date"], y=over["Weight"] * 100, name="주식 비중(%)", mode="lines",
                             line={"color": "rgba(242,245,248,0.7)", "width": 1, "shape": "hv"}, fill="tozeroy",
                             fillcolor="rgba(242,245,248,0.10)", showlegend=False,
                             hovertemplate="주식 비중 %{y:.0f}%<extra></extra>"), row=2, col=1)
    _style(fig, 520)
    fig.update_yaxes(type="log", row=1, col=1)
    fig.update_yaxes(range=[-5, 105], tickvals=[0, 50, 100], ticksuffix="%", row=2, col=1)
    fig.update_xaxes(tickformat="%Y")
    return fig


# ── Sections ───────────────────────────────────────────────────────────────────
def md(markup: str) -> None:
    st.markdown(ui.html(markup), unsafe_allow_html=True)


def index_panel(status: engine.IndexStatus, tag: str | None = None, selected: bool = False) -> str:
    disp = fmt_num(status.disparity, 1)
    heat = f"<b>이격도 {disp} 과열 · 한 단계 낮춤</b>" if status.overlay_active else f"이격도 {disp}"
    meta = f"{signal_chip(status.signal, '5·10개월선 ')}<span style='margin:0 9px;color:rgba(255,255,255,.24)'>·</span>{heat}"
    cash = 1 - status.final_weight
    name = f"{status.label} {status.key}" + (f" · {tag}" if tag else "")
    return f"""
      <div class="kr-panel{' sel' if selected else ''}">
        <div class="top"><span>{escape(name)}</span><span>{month_label(status.confirmed_month)} 확정</span></div>
        <div class="weight">{weight_text(status.final_weight)}<small>주식 · 현금 {weight_text(cash)}</small></div>
        <div class="meta">{meta}</div>
      </div>
    """


def render_banners(statuses: list[engine.IndexStatus], monthly_by_key: dict, today: date) -> None:
    confirmed = [s for s in statuses if s.just_confirmed]
    if confirmed:
        changes, same = [], []
        for s in confirmed:
            monthly = monthly_by_key[s.key]
            prev = monthly.iloc[-2]["Signal"] if len(monthly) >= 2 else None
            if prev and prev != s.signal:
                changes.append(f"{s.label} {weight_text(engine.SIGNAL_WEIGHT[prev])} → {weight_text(engine.SIGNAL_WEIGHT[s.signal])}")
            else:
                same.append(s.label)
        if changes:
            md(f"<div class='tj-note warn'>{month_label(confirmed[0].confirmed_month)} 신호 변경 · {escape(', '.join(changes))}</div>")
        if same:
            md(f"<div class='tj-note ok'>{month_label(confirmed[0].confirmed_month)} 신호 확정 · {escape(', '.join(same))} 유지</div>")
    if is_last_weekday_of_month(today):
        md("<div class='tj-note warn'>오늘 종가로 다음 달 비중 확정</div>")


def zone_position(price: float, red: float, green: float) -> float:
    """Where a price sits on the zone bar, in % of its width. The yellow zone
    (red..green) is the middle half; red and green get a quarter each."""
    span = (green - red) or price * 0.1
    if price < red:
        pos = 25 - (red - price) / (span * 0.5) * 25
    elif price >= green:
        pos = 75 + (price - green) / (span * 0.5) * 25
    else:
        pos = 25 + (price - red) / span * 50
    return max(3.0, min(97.0, pos))


def render_detail(status: engine.IndexStatus, today: date, eyebrow: str) -> None:
    """This month at a glance: one bar showing which signal the latest close
    would give at month-end, with the two prices that separate the zones."""
    d = price_digits(status.key)
    left = weekdays_left_in_month(today)
    red, green, close = status.red_below, status.green_above, status.last_close
    pos = zone_position(close, red, green)
    live = status.live_signal
    w = lambda sig: weight_text(engine.SIGNAL_WEIGHT[sig])
    to_green = (green / close - 1) * 100
    to_red = (red / close - 1) * 100
    foot = [f"100%까지 {fmt_pct(to_green)}" if close < green else "100% 구간",
            f"0%까지 {fmt_pct(to_red)}" if close >= red else "0% 구간"]
    if status.disparity_trigger:
        foot.append(f"과열 {fmt_num(status.disparity_trigger, d)} ({fmt_pct((status.disparity_trigger / close - 1) * 100)})")
    if 0 < left <= 5:
        foot.append(f"<b>월말까지 {left}거래일</b>")
    heat = ""
    if status.overlay_active:
        heat = (f"<div class='tj-note warn' style='margin:.9rem 0 0'>이격도 {fmt_num(status.disparity, 1)} 과열 · "
                f"주식 {weight_text(status.final_weight)}로 한 단계 낮춤</div>")
    md(f"""
        <div class="kr-zone">
          <div class="kr-zone-head"><span>이달 말 비중</span>
            <span>현재 <b>{fmt_num(close, d)}</b> · {ui.kdate(status.last_date)}</span></div>
          <div class="kr-bar">
            <div class="seg{' on' if live == 'red' else ''}">{w('red')}</div>
            <div class="seg{' on' if live == 'yellow' else ''}">{w('yellow')}</div>
            <div class="seg{' on' if live == 'green' else ''}">{w('green')}</div>
            <div class="kr-marker" style="left:{pos:.1f}%"></div>
          </div>
          <div class="kr-ticks">
            <span style="left:25%">{fmt_num(red, d)}</span>
            <span style="left:75%">{fmt_num(green, d)}</span>
          </div>
          <div class="kr-zone-foot">{' · '.join(foot)}</div>
          {heat}
        </div>
    """)


def render_backtest_table(backtests: dict) -> None:
    over, base = backtests["overlay"], backtests["base"]
    rows = [
        ("그냥 보유", over["hold"], "-", False),
        ("5개월선만", base["system"], f"{base['trades']}회", False),
        (f"5개월선 + 이격도{engine.DEV_THRESHOLD:.0f}", over["system"], f"{over['trades']}회", True),
    ]
    body = "".join(
        f"<tr class='{'best' if best else ''}'><td>{escape(name)}</td>"
        f"<td class='num'>{fmt_pct(stats['cagr'] * 100, 2, sign=False)}</td>"
        f"<td class='num'>{fmt_pct(stats['mdd'] * 100, 1, sign=False)}</td>"
        f"<td class='num'>{stats['total'] + 1:,.2f}배</td><td class='num'>{trades}</td></tr>"
        for name, stats, trades, best in rows
    )
    md(
        f"""
        <div class="tj-table-wrap"><table class="tj-table">
          <thead><tr><th>방식</th><th>연 수익률</th><th>최대 낙폭</th><th>누적</th><th>비중 변경</th></tr></thead>
          <tbody>{body}</tbody>
        </table></div>
        <div class="tj-caption">{over['start']:%Y.%m} ~ {over['end']:%Y.%m} · 배당 제외 · 매매비용 0.1% · 과거 성과는 미래를 보장하지 않음</div>
        """
    )


def render_rule() -> None:
    with st.expander("규칙"):
        md(
            f"""
            <div class="kr-rule">
            <b>기본 비중 · 5·10개월선</b><br>
            월말 종가가 5개월·10개월 월말 평균 둘 다 위 100%, 하나만 위 50%, 둘 다 아래 0%. 다음 달 내내 유지.<br><br>
            <b>과열 · 60일 이격도 {engine.DEV_THRESHOLD:.0f}</b><br>
            이격도 = 종가 ÷ 60거래일 평균 × 100. {engine.DEV_THRESHOLD:.0f} 이상인 동안 한 단계 낮춤(100→50, 50→0).<br><br>
            <b>근거</b><br>
            『돈을 불러오는 TIP』의 비중 규칙(이격도 130, 5개월선, 주봉 RSI 70)을 코스피 2004~·코스닥 2001~ 일봉으로 검증.
            5개월선이 뼈대, 이격도는 120에서 수익률·낙폭 모두 개선(코스닥은 130 도달 이력 없음). RSI 70은 과다 발동으로 제외.<br><br>
            <b>개별 종목</b><br>
            같은 계산 적용. 규칙은 지수 기준 검증이므로 백테스트 함께 확인. 종목은 KRX(KIND), ETF는 네이버 금융 목록(매일 갱신).<br><br>
            <b>한계</b><br>
            월중 급락은 피할 수 없음 · 헛신호 있음 · 투자 권유 아님.
            </div>
            """
        )


# ── Search ─────────────────────────────────────────────────────────────────────
@dataclass
class Target:
    """Whatever the detail section is showing: an index or a searched stock."""
    status: engine.IndexStatus
    daily: pd.DataFrame
    monthly: pd.DataFrame
    symbol: str
    start_year: int
    market: str | None = None

    @property
    def is_stock(self) -> bool:
        return self.status.key not in engine.INDEXES


def market_text(market: str | None) -> str:
    return engine.MARKET_LABEL.get(market or "", "코드로 조회")


def resolve_search(query: str, today: date, day_key: str) -> Target | None:
    """Turn the search box into a stock Target, showing any message itself."""
    q = query.strip()
    listing, live = load_listing(day_key)
    hits = engine.search_listing(listing, q)
    if engine.should_search_etfs(q, hits):
        hits = engine.combine_hits(hits, load_etf_search(engine.normalize_text(q), q, day_key))
    code = q.upper().replace(" ", "")

    if hits.empty:
        if not engine.CODE_PATTERN.match(code):
            hint = "" if live else " · 저장된 목록 기준(최근 상장 종목은 6자리 코드로 검색)"
            st.info(f"'{q}' 검색 결과 없음 · 이름 일부(나스닥100, 코스닥150) 또는 6자리 코드(069500){hint}")
            return None
        pick = {"code": code, "name": "", "market": ""}
    elif len(hits) == 1:
        pick = hits.iloc[0].to_dict()
    else:
        # An exact name/code match opens right away; the rest stay in the list.
        wanted = "".join(engine.query_tokens(q))
        exact_first = (engine.normalize_text(hits.at[0, "name"]) == wanted) or (hits.at[0, "code"].lower() == wanted)
        label = f"검색 결과 {len(hits)}개" + (" · 이름을 더 입력하면 좁혀짐" if len(hits) >= 30 else "")
        idx = st.selectbox(
            label, list(hits.index), index=0 if exact_first else None, placeholder="종목 선택",
            format_func=lambda i: f"{hits.at[i, 'name']} · {hits.at[i, 'code']} · {market_text(hits.at[i, 'market'])}",
            key=f"kr_pick_{engine.normalize_text(q)}",
        )
        if idx is None:
            return None
        pick = hits.loc[idx].to_dict()

    with st.spinner(f"{pick['name'] or pick['code']} 불러오는 중"):
        try:
            found = load_stock(pick["code"], pick.get("market") or "", day_key)
        except Exception:
            found = None
    if found is None:
        st.warning(f"{pick['name'] or pick['code']} 시세 없음")
        return None

    name = pick["name"] or found["yahoo_name"]
    try:
        status = engine.current_status(pick["code"], found["daily"], today, label=name)
    except engine.HistoryTooShort:
        st.info(f"{name} · 데이터 부족 (월말 종가 10개월, 60거래일 필요)")
        return None
    monthly = engine.monthly_signals(found["daily"], today).dropna(subset=["Signal"])
    return Target(status, found["daily"], monthly, found["symbol"], engine.STOCK_START_YEAR, pick.get("market") or None)


def pick_index(key: str) -> None:
    """Card tap: show that index and leave search mode."""
    st.session_state["kr_index"] = key
    st.session_state["kr_query"] = ""


def sync_query_param(query: str) -> None:
    """Keep ?q= in the address bar equal to the search, so the URL can be shared."""
    current = st.query_params.get("q") or ""
    if query == current:
        return
    if query:
        st.query_params["q"] = query
        st.session_state["_kr_q_seen"] = query
    elif "q" in st.query_params:
        del st.query_params["q"]


# ── Page ───────────────────────────────────────────────────────────────────────
def main() -> None:
    today = engine.kst_today()
    day_key = today.isoformat()

    st.markdown(ui.BASE_CSS, unsafe_allow_html=True)
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
    st.markdown(ui.nav_html("korea"), unsafe_allow_html=True)
    hero_slot = st.empty()
    hero_slot.markdown(ui.hero_html("Korea Market Signals", "불러오는 중", self_key="korea",
                                    extra_meta="코스피 · 코스닥 주식/현금 비중"), unsafe_allow_html=True)

    dailies, statuses, monthly_by_key, errors = {}, {}, {}, []
    with st.spinner("불러오는 중"):
        for key in engine.INDEXES:
            try:
                daily = load_daily(key, day_key)
                if daily.empty:
                    raise ValueError("empty")
                dailies[key] = daily
                statuses[key] = engine.current_status(key, daily, today)
                monthly_by_key[key] = engine.monthly_signals(daily, today).dropna(subset=["Signal"])
            except Exception:
                errors.append(engine.INDEXES[key]["label"])

    updated = max((s.last_date for s in statuses.values()), default=None)
    hero_slot.markdown(ui.hero_html(
        "Korea Market Signals",
        (f"{ui.kdate(updated)} 종가" + (f" · {closed}" if (closed := closed_weekdays_text(updated, today)) else ""))
        if updated is not None else "불러오기 실패",
        dot="live" if statuses else "closed", self_key="korea",
        extra_meta="코스피 · 코스닥 주식/현금 비중",
    ), unsafe_allow_html=True)

    if errors:
        st.warning(f"{', '.join(errors)} 데이터 불러오기 실패 · 잠시 후 새로고침")
    if not statuses:
        st.stop()

    render_banners(list(statuses.values()), monthly_by_key, today)
    # ?q= (shared link) opens that search once.
    shared_q = st.query_params.get("q")
    if shared_q and st.session_state.get("_kr_q_seen") != shared_q:
        st.session_state["_kr_q_seen"] = shared_q
        st.session_state["kr_query"] = str(shared_q)[:40]

    keys = list(statuses.keys())
    if st.session_state.get("kr_index") not in keys:
        st.session_state["kr_index"] = keys[0]
    searching = bool(str(st.session_state.get("kr_query") or "").strip())

    # The index cards are the picker: a tap selects (an invisible button covers each card).
    for col, key in zip(st.columns(len(keys), gap="large"), keys):
        with col:
            md(index_panel(statuses[key], selected=(key == st.session_state["kr_index"] and not searching)))
            st.button(f"{engine.INDEXES[key]['label']} 보기", key=f"kr_card_{key}", on_click=pick_index, args=(key,))

    query = st.text_input(
        "종목 · ETF 검색", key="kr_query", label_visibility="collapsed",
        placeholder="종목 · ETF 검색 · 삼성전자, 005930, KODEX 레버리지",
    )
    sync_query_param(query.strip())
    if query.strip():
        target = resolve_search(query, today, day_key)
        if target is None:
            render_rule()
            st.markdown(ui.footer_html(), unsafe_allow_html=True)
            return
        md("<div class='kr-panels single'>" + index_panel(target.status, market_text(target.market), selected=True) + "</div>")
        md("<div class='tj-caption' style='margin:.2rem 0 0'>규칙은 지수 기준으로 검증 · 개별 종목은 백테스트 참고</div>")
        eyebrow = ""
    else:
        selected = st.session_state["kr_index"]
        cfg = engine.INDEXES[selected]
        target = Target(statuses[selected], dailies[selected], monthly_by_key[selected], cfg["symbol"], cfg["start_year"], selected)
        eyebrow = ""

    status, daily, monthly = target.status, target.daily, target.monthly
    digits = price_digits(status.key)
    render_detail(status, today, eyebrow)

    tab_month, tab_disp, tab_bt = st.tabs(["월봉 신호", "이격도", "백테스트"])
    with tab_month:
        st.plotly_chart(build_monthly_chart(monthly, status, digits=digits), use_container_width=True, config=PLOT_CONFIG)
        md(signal_key_html())
        export = monthly.copy()
        export["Month"] = export["Month"].astype(str)
        export["Date"] = pd.to_datetime(export["Date"]).dt.strftime("%Y-%m-%d")
        st.download_button(
            label="월별 기록 CSV",
            data=export.to_csv(index=False, encoding="utf-8-sig"),
            file_name=f"{status.key}_monthly_signals_{today:%Y%m%d}.csv",
            mime="text/csv",
        )
    with tab_disp:
        st.plotly_chart(build_disparity_chart(daily, digits=digits), use_container_width=True, config=PLOT_CONFIG)
    with tab_bt:
        try:
            backtests = load_backtests(target.symbol, target.start_year, day_key)
        except Exception:
            backtests = None
            st.info("백테스트 계산 실패")
        if backtests:
            st.plotly_chart(build_backtest_chart(backtests), use_container_width=True, config=PLOT_CONFIG)
            render_backtest_table(backtests)

    render_rule()
    st.markdown(ui.footer_html(), unsafe_allow_html=True)
