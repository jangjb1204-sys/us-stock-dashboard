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

THREADS_URL = "https://www.threads.net/@30s_tech_j"
CACHE_TTL_SECONDS = 60 * 60 * 3
LISTING_PATH = Path(__file__).resolve().parent / "korea_stock_list.csv"

SIGNAL_COLOR = {"green": "#34c77b", "yellow": "#f0c35a", "red": "#ff6b7a"}
PLOT_CONFIG = {"displayModeBar": False, "responsive": True, "scrollZoom": False, "doubleClick": False}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"], .stApp {
    font-family: 'DM Sans', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif !important;
    background: #03050a !important;
    color: #f5f5f7 !important;
}
.stApp::before {
    content: ""; position: fixed; inset: 0; pointer-events: none;
    background:
        radial-gradient(circle at 12% 0%, rgba(40,92,160,0.18), transparent 30%),
        radial-gradient(circle at 88% 2%, rgba(50,105,190,0.10), transparent 28%);
}
#MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="stHeader"], [data-testid="collapsedControl"], [data-testid="stSidebar"] { display:none!important; }
.block-container { max-width: 1240px; padding: 3.6rem 2.6rem 3rem !important; position: relative; z-index: 1; }
.kr-hero { display:flex; justify-content:space-between; align-items:flex-start; gap:20px; margin-bottom:2.2rem; }
.kr-hero h1 { margin:0; font-size:2.6rem; line-height:1.05; font-weight:720; letter-spacing:-0.04em; color:#f5f5f7; }
.kr-hero h1 a { color:inherit!important; text-decoration:none!important; }
.kr-title-row { display:flex; align-items:center; gap:13px; }
.kr-dot { width:9px; height:9px; border-radius:999px; background:#2F80FF; box-shadow:0 0 16px rgba(47,128,255,.45); }
.kr-meta { margin-top:.7rem; color:#8e8e93; font-size:.8rem; }
.kr-meta strong { color:#b7bcc7; font-family:'DM Mono', monospace; font-weight:500; }
.kr-switch { display:inline-flex; align-items:center; gap:8px; margin-top:.4rem; padding:8px 14px; border-radius:999px; border:1px solid rgba(255,255,255,.10); background:rgba(255,255,255,.035); color:#d7dce5!important; font-size:.8rem; font-weight:650; text-decoration:none!important; white-space:nowrap; }
.kr-switch:hover { background:rgba(255,255,255,.07); }
.kr-banner { border-radius:16px; padding:12px 16px; margin:0 0 1rem; font-size:.92rem; font-weight:600; border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.03); color:#e9ebef; }
.kr-banner.warn { border-color:rgba(240,195,90,.35); background:rgba(240,195,90,.08); color:#f6dc9c; }
.kr-banner.ok { border-color:rgba(52,199,123,.30); background:rgba(52,199,123,.07); color:#a9ebc7; }
.kr-cards { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-bottom:1.6rem; }
.kr-cards.single { grid-template-columns:minmax(0,1fr); max-width:620px; margin-bottom:1rem; }
.kr-card { border:1px solid rgba(255,255,255,.08); border-radius:22px; padding:20px 22px; background:rgba(255,255,255,.025); }
.kr-card .top { display:flex; justify-content:space-between; align-items:center; color:#8e8e93; font-size:.78rem; font-weight:720; letter-spacing:.05em; text-transform:uppercase; }
.kr-card .weight { margin-top:.7rem; font-family:'DM Mono', monospace; font-size:2.7rem; line-height:1; color:#f5f5f7; }
.kr-card .weight small { font-family:'DM Sans', sans-serif; font-size:.95rem; color:#8e8e93; margin-left:8px; }
.kr-card .sub { margin-top:.8rem; display:flex; flex-wrap:wrap; gap:8px; }
.chip { display:inline-flex; align-items:center; gap:6px; border-radius:999px; padding:5px 11px; font-size:.78rem; font-weight:700; border:1px solid rgba(255,255,255,.09); background:rgba(255,255,255,.045); color:#e9ebef; white-space:nowrap; }
.chip.green { background:rgba(52,199,123,.12); color:#a9ebc7; border-color:rgba(52,199,123,.28); }
.chip.yellow { background:rgba(240,195,90,.12); color:#f6dc9c; border-color:rgba(240,195,90,.28); }
.chip.red { background:rgba(255,107,122,.12); color:#ffb6bf; border-color:rgba(255,107,122,.26); }
.chip.hot { background:rgba(255,107,122,.18); color:#ffd0d6; border-color:rgba(255,107,122,.38); }
.kr-section { color:#8e8e93; font-size:.78rem; font-weight:720; letter-spacing:.055em; text-transform:uppercase; margin:1.8rem 0 .8rem; }
.kr-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; }
.kr-item { border-top:1px solid rgba(255,255,255,.08); padding-top:1.1rem; min-height:96px; }
.kr-item .label { color:#8e8e93; font-size:.74rem; font-weight:720; letter-spacing:.04em; }
.kr-item .value { margin-top:.45rem; font-family:'DM Mono', monospace; font-size:1.65rem; color:#f5f5f7; line-height:1.05; }
.kr-item .hint { margin-top:.45rem; color:#8e8e93; font-size:.8rem; line-height:1.35; }
.kr-sentence { margin:1.2rem 0 .2rem; color:#d7dce5; font-size:.96rem; line-height:1.55; }
.kr-table-wrap { overflow-x:auto; border-top:1px solid rgba(255,255,255,.08); margin-top:.6rem; }
.kr-table { width:100%; border-collapse:collapse; min-width:620px; }
.kr-table th { padding:11px 12px; text-align:left; color:#8e8e93; font-size:.72rem; font-weight:720; letter-spacing:.04em; border-bottom:1px solid rgba(255,255,255,.075); }
.kr-table td { padding:11px 12px; color:#e9ebef; font-size:.86rem; border-bottom:1px solid rgba(255,255,255,.05); }
.kr-table td.num { font-family:'DM Mono', monospace; color:#d7dce5; white-space:nowrap; }
.kr-table tr.best td { background:rgba(47,128,255,.07); }
.kr-note { color:#8e8e93; font-size:.82rem; line-height:1.55; margin-top:.8rem; }
.kr-rule { color:#c9ced8; font-size:.9rem; line-height:1.7; }
.kr-rule b { color:#f5f5f7; }
.kr-footer { margin:2.6rem 0 .4rem; }
.kr-footer a { color:rgba(245,245,247,.34); font-size:1rem; font-weight:650; text-decoration:none!important; }
div[role="radiogroup"] label { font-weight:650; }
.stButton > button, div[data-testid="stDownloadButton"] button { border-radius:999px!important; border:1px solid rgba(255,255,255,.08)!important; background:rgba(255,255,255,.035)!important; color:#f5f5f7!important; font-weight:700!important; }
button[data-baseweb="tab"] p { font-weight:700!important; }
@media (max-width:900px){ .block-container{padding:2.8rem 1.3rem 2.2rem!important;} .kr-grid{grid-template-columns:repeat(2,minmax(0,1fr));} .kr-hero h1{font-size:2.2rem;} }
@media (max-width:640px){
    .block-container{padding:2.4rem .85rem 2rem!important;}
    .kr-hero{flex-direction:column; gap:10px; margin-bottom:1.5rem;}
    .kr-hero h1{font-size:1.9rem;}
    .kr-cards{grid-template-columns:1fr;}
    .kr-card .weight{font-size:2.3rem;}
    .kr-item .value{font-size:1.35rem;}
}
</style>
"""


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
    """KRX's list of KOSPI/KOSDAQ companies; (listing, is_live). Falls back to
    the copy shipped in the repo when KIND can't be reached."""
    try:
        return engine.fetch_krx_listing(), True
    except Exception:
        return engine.load_listing_csv(LISTING_PATH), False


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


def signal_chip(signal: str, prefix: str = "") -> str:
    label = f"{prefix}{engine.SIGNAL_EMOJI[signal]} {engine.SIGNAL_LABEL[signal]}"
    return f"<span class='chip {signal}'>{escape(label)}</span>"


def month_label(period: pd.Period) -> str:
    return f"{period.year}년 {period.month}월"


def is_last_weekday_of_month(day: date) -> bool:
    if day.weekday() >= 5:
        return False
    nxt = day + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt.month != day.month


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
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#05070d",
        font={"family": "DM Sans, sans-serif", "color": "#d7dce5", "size": 11},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1, "font": {"size": 11}},
        hovermode="x unified",
        dragmode=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.055)", zeroline=False, fixedrange=True,
                     tickfont={"color": "rgba(245,245,247,0.54)", "size": 10})
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.075)", zeroline=False, fixedrange=True,
                     tickfont={"color": "rgba(245,245,247,0.46)", "size": 10})
    return fig


def build_monthly_chart(monthly: pd.DataFrame, status: engine.IndexStatus, years: int = 6, digits: int = 2) -> go.Figure:
    yfmt = f"%{{y:,.{digits}f}}"
    cutoff = status.confirmed_month - 12 * years
    data = monthly[monthly["Month"] >= cutoff].copy()
    x = data["Month"].dt.to_timestamp(how="end").dt.normalize()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=data["Close"], name="월말 종가", mode="lines",
                             line={"color": "#f5f5f7", "width": 2},
                             hovertemplate="%{x|%Y-%m}<br>월말 종가 " + yfmt + "<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=data["MA5"], name="5개월선", mode="lines",
                             line={"color": "#5aa6ff", "width": 1.6, "dash": "dot"},
                             hovertemplate="5개월선 " + yfmt + "<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=data["MA10"], name="10개월선", mode="lines",
                             line={"color": "#b58cff", "width": 1.6, "dash": "dot"},
                             hovertemplate="10개월선 " + yfmt + "<extra></extra>"))
    for sig in ("green", "yellow", "red"):
        part = data[data["Signal"] == sig]
        if part.empty:
            continue
        fig.add_trace(go.Scatter(
            x=part["Month"].dt.to_timestamp(how="end").dt.normalize(), y=part["Close"],
            name=engine.SIGNAL_LABEL[sig], mode="markers",
            marker={"size": 8, "color": SIGNAL_COLOR[sig], "line": {"width": 1, "color": "#05070d"}},
            hovertemplate=f"{engine.SIGNAL_LABEL[sig]}<extra></extra>",
        ))

    # This month so far, plus the two lines its month-end close has to clear.
    fig.add_trace(go.Scatter(
        x=[status.last_date], y=[status.last_close], name="이번 달(진행 중)", mode="markers",
        marker={"size": 10, "color": "rgba(0,0,0,0)", "line": {"width": 2, "color": SIGNAL_COLOR[status.live_signal]}},
        hovertemplate="이번 달 최근 종가 " + yfmt + "<extra></extra>",
    ))
    fig.add_hline(y=status.green_above, line={"color": SIGNAL_COLOR["green"], "width": 1, "dash": "dash"},
                  annotation_text=f"초록불 기준 {status.green_above:,.0f}", annotation_position="top left",
                  annotation_font={"color": SIGNAL_COLOR["green"], "size": 10})
    fig.add_hline(y=status.red_below, line={"color": SIGNAL_COLOR["red"], "width": 1, "dash": "dash"},
                  annotation_text=f"빨간불 기준 {status.red_below:,.0f}", annotation_position="bottom left",
                  annotation_font={"color": SIGNAL_COLOR["red"], "size": 10})
    _style(fig, 440)
    fig.update_xaxes(tickformat="%y.%m")
    return fig


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
                             line={"color": "#f0c35a", "width": 1.3, "dash": "dot"},
                             hovertemplate="60일 평균 " + yfmt + "<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=hot["Date"], y=hot["Close"], name=f"이격도 {engine.DEV_THRESHOLD:.0f}↑ (과열)",
                             mode="markers", marker={"size": 6, "color": SIGNAL_COLOR["red"]},
                             hovertemplate="과열 " + yfmt + "<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data["Date"], y=data["Disparity"], name="60일 이격도", mode="lines",
                             line={"color": "#5aa6ff", "width": 1.6},
                             hovertemplate="이격도 %{y:.1f}<extra></extra>"), row=2, col=1)
    fig.add_hline(y=engine.DEV_THRESHOLD, line={"color": SIGNAL_COLOR["red"], "width": 1, "dash": "dash"}, row=2, col=1)
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
                             line={"color": "#5aa6ff", "width": 1.5},
                             hovertemplate="5개월선만 %{y:.2f}배<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=over["Date"], y=over["System"], name=f"5개월선 + 이격도{engine.DEV_THRESHOLD:.0f}",
                             mode="lines", line={"color": "#34c77b", "width": 2},
                             hovertemplate="5개월선+이격도 %{y:.2f}배<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=over["Date"], y=over["Weight"] * 100, name="주식 비중(%)", mode="lines",
                             line={"color": "#34c77b", "width": 1, "shape": "hv"}, fill="tozeroy",
                             fillcolor="rgba(52,199,123,0.18)", showlegend=False,
                             hovertemplate="주식 비중 %{y:.0f}%<extra></extra>"), row=2, col=1)
    _style(fig, 520)
    fig.update_yaxes(type="log", row=1, col=1)
    fig.update_yaxes(range=[-5, 105], tickvals=[0, 50, 100], ticksuffix="%", row=2, col=1)
    fig.update_xaxes(tickformat="%Y")
    return fig


# ── Sections ───────────────────────────────────────────────────────────────────
def render_hero(updated: str) -> None:
    st.markdown(
        f"""
        <div class="kr-hero">
          <div>
            <div class="kr-title-row"><span class="kr-dot"></span>
              <h1><a href="?dashboard=korea" target="_self">Korea Market Signals</a></h1></div>
            <div class="kr-meta">코스피 · 코스닥 주식/현금 비중 신호 · 기준 종가 <strong>{escape(updated)}</strong></div>
          </div>
          <a class="kr-switch" href="?dashboard=us" target="_self">🇺🇸 US Market Signals →</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_index_card(status: engine.IndexStatus, tag: str | None = None) -> str:
    chips = [signal_chip(status.signal, "5개월선 ")]
    disp = fmt_num(status.disparity, 1)
    if status.overlay_active:
        chips.append(f"<span class='chip hot'>🔥 이격도 {disp} · 과열</span>")
    else:
        chips.append(f"<span class='chip'>이격도 {disp}</span>")
    cash = 1 - status.final_weight
    return f"""
      <div class="kr-card">
        <div class="top"><span>{escape(status.label)} {escape(status.key)}{escape(" · " + tag) if tag else ""}</span><span>{month_label(status.confirmed_month)} 확정</span></div>
        <div class="weight">{weight_text(status.final_weight)}<small>주식 · 현금 {weight_text(cash)}</small></div>
        <div class="sub">{''.join(chips)}</div>
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
                changes.append(f"{s.label} {engine.SIGNAL_EMOJI[prev]}→{engine.SIGNAL_EMOJI[s.signal]}")
            else:
                same.append(s.label)
        if changes:
            st.markdown(f"<div class='kr-banner warn'>⚠️ 신호 변화: {escape(', '.join(changes))} — 오늘 주식 비중을 새 신호에 맞출 차례예요.</div>",
                        unsafe_allow_html=True)
        if same:
            st.markdown(f"<div class='kr-banner ok'>✅ {month_label(confirmed[0].confirmed_month)} 신호 확정: {escape(', '.join(same))} 그대로 유지</div>",
                        unsafe_allow_html=True)
    if is_last_weekday_of_month(today):
        st.markdown("<div class='kr-banner warn'>📌 오늘 종가로 다음 달 신호가 확정됩니다.</div>", unsafe_allow_html=True)


def render_detail(status: engine.IndexStatus, today: date) -> None:
    which, price, move = status.nearest_boundary
    d = price_digits(status.key)
    left = weekdays_left_in_month(today)
    urgency = " (월말까지 평일 5일 이내!)" if 0 < left <= 5 else ""
    trigger = status.disparity_trigger
    trigger_move = (trigger / status.last_close - 1) * 100 if trigger else None

    items = [
        ("최근 종가", fmt_num(status.last_close, d), status.last_date.strftime("%Y-%m-%d")),
        ("이달 말 초록불 기준", f"≥ {fmt_num(status.green_above, d)}", f"최근 종가 대비 {fmt_pct((status.green_above / status.last_close - 1) * 100)}"),
        ("이달 말 빨간불 기준", f"< {fmt_num(status.red_below, d)}", f"최근 종가 대비 {fmt_pct((status.red_below / status.last_close - 1) * 100)}"),
        ("과열(이격도 120) 가격", fmt_num(trigger, d), f"오늘 이 가격 이상이면 비중 한 단계↓ ({fmt_pct(trigger_move)})"),
    ]
    st.markdown(
        "<div class='kr-grid'>" + "".join(
            f"<div class='kr-item'><div class='label'>{escape(label)}</div><div class='value'>{escape(value)}</div><div class='hint'>{escape(hint)}</div></div>"
            for label, value, hint in items
        ) + "</div>",
        unsafe_allow_html=True,
    )

    live = f"{engine.SIGNAL_EMOJI[status.live_signal]} {engine.SIGNAL_LABEL[status.live_signal]}"
    base_note = (f"지난달 말({month_label(status.confirmed_month)}) 종가 {fmt_num(status.confirmed_close, d)}가 "
                 f"5개월선 {fmt_num(status.ma5, d)} / 10개월선 {fmt_num(status.ma10, d)}과 비교돼 "
                 f"<b>{engine.SIGNAL_LABEL[status.signal]}</b>(기본 비중 {weight_text(status.base_weight)})입니다.")
    if status.overlay_active:
        overlay_note = f" 지금 60일 이격도가 {fmt_num(status.disparity, 1)}로 과열이라 한 단계 낮춘 <b>{weight_text(status.final_weight)}</b>가 권장 비중이에요."
    else:
        overlay_note = f" 60일 이격도 {fmt_num(status.disparity, 1)}는 과열 기준(120) 아래라 비중을 더 줄이지 않아요."
    live_note = f" 지금 수준으로 이달이 끝나면 {live}이고, {which}로 바뀌려면 {fmt_pct(move)} 움직여야 해요{urgency}."
    st.markdown(f"<div class='kr-sentence'>{base_note}{overlay_note}{live_note}</div>", unsafe_allow_html=True)


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
    st.markdown(
        f"""
        <div class="kr-table-wrap"><table class="kr-table">
          <thead><tr><th>방식</th><th>연 수익률</th><th>최대 낙폭</th><th>누적</th><th>비중 변경</th></tr></thead>
          <tbody>{body}</tbody>
        </table></div>
        <div class="kr-note">{over['start']:%Y-%m-%d} ~ {over['end']:%Y-%m-%d} ({over['years']:.1f}년) · 가격 기준(배당 제외) ·
        현금 이자 0% · 비중 바꿀 때 0.1% 비용 · 신호가 난 날 종가로 매매했다고 가정.
        과거에 이랬다고 앞으로도 그렇다는 보장은 없어요.</div>
        """,
        unsafe_allow_html=True,
    )


def render_history_table(monthly: pd.DataFrame, digits: int = 2) -> None:
    recent = monthly.dropna(subset=["Signal"]).iloc[::-1].head(12)
    body = "".join(
        f"<tr><td>{row.Month.year}-{row.Month.month:02d}</td>"
        f"<td class='num'>{row.Close:,.{digits}f}</td><td class='num'>{row.MA5:,.{digits}f}</td><td class='num'>{row.MA10:,.{digits}f}</td>"
        f"<td>{signal_chip(row.Signal)}</td><td class='num'>{weight_text(row.Weight)}</td></tr>"
        for row in recent.itertuples()
    )
    st.markdown(
        f"""
        <div class="kr-table-wrap"><table class="kr-table">
          <thead><tr><th>월</th><th>월말 종가</th><th>5개월선</th><th>10개월선</th><th>신호</th><th>기본 비중</th></tr></thead>
          <tbody>{body}</tbody>
        </table></div>
        <div class="kr-note">최근 12개월 · 전체 기록은 CSV로 받을 수 있어요. 기본 비중은 다음 달 한 달 동안 적용돼요. 달 중간에 60일 이격도가 120 이상이 되면 그동안만 한 단계 더 낮춥니다.</div>
        """,
        unsafe_allow_html=True,
    )


def render_rule() -> None:
    with st.expander("규칙 설명 (어떻게 계산하나요?)"):
        st.markdown(
            f"""
            <div class="kr-rule">
            <b>1. 기본 비중 — 5개월선·10개월선</b><br>
            매달 마지막 거래일 종가(월말 종가)를 최근 5개월·10개월 월말 종가의 평균과 비교해요.
            둘 다 위면 🟢 주식 100%, 하나만 위면 🟡 50%, 둘 다 아래면 🔴 0%(전부 현금).
            신호는 월말 종가로 정해지고 다음 달 내내 유지돼요.<br><br>
            <b>2. 과열 보조 — 60일 이격도 {engine.DEV_THRESHOLD:.0f}</b><br>
            이격도 = 오늘 종가 ÷ 최근 60거래일 평균 × 100. {engine.DEV_THRESHOLD:.0f}이면 평균보다 {engine.DEV_THRESHOLD - 100:.0f}% 높다는 뜻이에요.
            이 값이 {engine.DEV_THRESHOLD:.0f} 이상인 동안에만 비중을 한 단계 낮춰요(100%→50%, 50%→0%). 내려오면 원래대로.<br><br>
            <b>왜 이 조합?</b> 『돈을 불러오는 TIP』의 비중 규칙(이격도 130, 5개월선, 주봉 RSI 70)을
            코스피 2004~·코스닥 2001~ 일봉으로 검증해 보니, 5개월선이 뼈대 역할을 했고
            이격도는 130·125보다 120일 때 수익률과 낙폭이 함께 좋아졌어요(코스닥은 역대 130을 한 번도 넘지 않음).
            RSI 70을 더하면 너무 자주 발동해 코스피 수익률이 크게 깎여서 뺐어요.<br><br>
            <b>개별 종목</b> 검색한 종목에도 같은 계산을 그대로 적용해요. 규칙 자체는 지수로 검증했으니 종목마다 백테스트 결과를 같이 보세요.
            종목 목록은 KRX(KIND) 상장법인 목록을 쓰고, 목록에 없는 ETF 등은 6자리 코드로 찾을 수 있어요.<br><br>
            <b>한계</b> 한 달 안에 몰아치는 급락은 월간 신호로 피할 수 없고, 헛신호도 있어요.
            과거 데이터로 만든 규칙을 기계적으로 계산한 결과이며 투자 권유가 아닙니다.
            </div>
            """,
            unsafe_allow_html=True,
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
    code = q.upper().replace(" ", "")

    if hits.empty:
        if not engine.CODE_PATTERN.match(code):
            hint = "" if live else " (KRX 목록을 지금 못 받아 저장된 목록으로 찾았어요 — 최근 상장 종목은 종목코드로 검색해 주세요.)"
            st.info(f"'{q}'에 맞는 코스피·코스닥 종목이 없어요. ETF는 6자리 종목코드로 검색할 수 있어요(예: 069500).{hint}")
            return None
        pick = {"code": code, "name": "", "market": ""}
    elif len(hits) == 1:
        pick = hits.iloc[0].to_dict()
    else:
        label = f"검색 결과 {len(hits)}개" + (" · 더 있으면 이름을 더 입력해 주세요" if len(hits) >= 30 else "")
        idx = st.selectbox(
            label, list(hits.index), index=None, placeholder="종목을 골라 주세요",
            format_func=lambda i: f"{hits.at[i, 'name']} · {hits.at[i, 'code']} · {market_text(hits.at[i, 'market'])}",
            key=f"kr_pick_{engine.normalize_text(q)}",
        )
        if idx is None:
            return None
        pick = hits.loc[idx].to_dict()

    with st.spinner(f"{pick['name'] or pick['code']} 데이터를 불러오는 중..."):
        try:
            found = load_stock(pick["code"], pick.get("market") or "", day_key)
        except Exception:
            found = None
    if found is None:
        st.warning(f"{pick['name'] or pick['code']} 시세를 지금 찾을 수 없어요.")
        return None

    name = pick["name"] or found["yahoo_name"]
    try:
        status = engine.current_status(pick["code"], found["daily"], today, label=name)
    except engine.HistoryTooShort:
        st.info(f"{name}은(는) 상장한 지 얼마 안 돼서 아직 계산할 수 없어요. 월말 종가 10개월치와 60거래일이 쌓여야 해요.")
        return None
    monthly = engine.monthly_signals(found["daily"], today).dropna(subset=["Signal"])
    return Target(status, found["daily"], monthly, found["symbol"], engine.STOCK_START_YEAR, pick.get("market") or None)


# ── Page ───────────────────────────────────────────────────────────────────────
def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    today = engine.kst_today()
    day_key = today.isoformat()

    dailies, statuses, monthly_by_key, errors = {}, {}, {}, []
    with st.spinner("코스피·코스닥 데이터를 불러오는 중..."):
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
    render_hero(updated.strftime("%Y-%m-%d") if updated is not None else "불러오기 실패")

    if errors:
        st.warning(f"{', '.join(errors)} 데이터를 지금 불러오지 못했어요. 잠시 후 새로고침해 주세요.")
    if not statuses:
        st.stop()

    render_banners(list(statuses.values()), monthly_by_key, today)
    st.markdown("<div class='kr-cards'>" + "".join(render_index_card(s) for s in statuses.values()) + "</div>",
                unsafe_allow_html=True)

    st.markdown("<div class='kr-section'>종목 검색</div>", unsafe_allow_html=True)
    query = st.text_input(
        "종목 검색", key="kr_query", label_visibility="collapsed",
        placeholder="코스피·코스닥 종목 이름 또는 코드 · 예: 삼성전자, 005930, 에코프로비엠",
    )
    target = resolve_search(query, today, day_key) if query.strip() else None

    if target is not None:
        st.markdown("<div class='kr-cards single'>" + render_index_card(target.status, market_text(target.market)) + "</div>",
                    unsafe_allow_html=True)
        st.markdown(
            "<div class='kr-banner'>ℹ️ 이 규칙은 코스피·코스닥 <b>지수</b>로 검증했어요. 개별 종목은 훨씬 크게 움직여서 "
            "같은 규칙이 잘 맞는다는 보장이 없으니, 아래 <b>백테스트</b> 탭에서 이 종목 결과를 꼭 같이 보세요. "
            "검색창을 비우면 지수로 돌아가요.</div>",
            unsafe_allow_html=True,
        )
    else:
        options = list(statuses.keys())
        selected = st.radio("지수", options, horizontal=True, key="kr_index",
                            format_func=lambda k: f"{engine.INDEXES[k]['label']} {k}")
        cfg = engine.INDEXES[selected]
        target = Target(statuses[selected], dailies[selected], monthly_by_key[selected], cfg["symbol"], cfg["start_year"], selected)

    status, daily, monthly = target.status, target.daily, target.monthly
    digits = price_digits(status.key)
    st.markdown(f"<div class='kr-section'>{escape(status.label)} · 이번 달 체크</div>", unsafe_allow_html=True)
    render_detail(status, today)

    tab_month, tab_disp, tab_bt, tab_hist = st.tabs(["월봉 신호", "이격도", "백테스트", "기록"])
    with tab_month:
        st.plotly_chart(build_monthly_chart(monthly, status, digits=digits), use_container_width=True, config=PLOT_CONFIG)
    with tab_disp:
        st.plotly_chart(build_disparity_chart(daily, digits=digits), use_container_width=True, config=PLOT_CONFIG)
    with tab_bt:
        try:
            backtests = load_backtests(target.symbol, target.start_year, day_key)
        except Exception:
            backtests = None
            st.info("백테스트를 계산하지 못했어요.")
        if backtests:
            st.plotly_chart(build_backtest_chart(backtests), use_container_width=True, config=PLOT_CONFIG)
            render_backtest_table(backtests)
    with tab_hist:
        render_history_table(monthly, digits)
        export = monthly.copy()
        export["Month"] = export["Month"].astype(str)
        export["Date"] = pd.to_datetime(export["Date"]).dt.strftime("%Y-%m-%d")
        st.download_button(
            label="월별 신호 CSV 다운로드",
            data=export.to_csv(index=False, encoding="utf-8-sig"),
            file_name=f"{status.key}_monthly_signals_{today:%Y%m%d}.csv",
            mime="text/csv",
        )

    render_rule()
    st.markdown(f"<div class='kr-footer'><a href='{THREADS_URL}' target='_blank' rel='noopener'>by 30s_tech_j</a></div>",
                unsafe_allow_html=True)
