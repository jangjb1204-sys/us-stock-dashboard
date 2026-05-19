from __future__ import annotations

from calendar import Calendar, month_name
from html import escape
from io import StringIO
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components


APP_DIR = Path(__file__).resolve().parent
SCAN_DIR = APP_DIR / "signal_scans"
REMOTE_SCAN_API_URL = "https://api.github.com/repos/jangjb1204-sys/puddle-signal-dashboard/contents/signal_scans?ref=main"
THREADS_URL = "https://www.threads.net/@30s_tech_j"
CENTRAL_TZ = ZoneInfo("America/Chicago")
CACHE_TTL_SECONDS = 60
CHART_CACHE_TTL_SECONDS = 60 * 60 * 6
calendar_component = components.declare_component("puddle_calendar", path=str(APP_DIR / "calendar_component"))
signal_table_component = components.declare_component("puddle_signal_table", path=str(APP_DIR / "signal_table_component"))

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"], .stApp {
    font-family: 'DM Sans', sans-serif !important;
    background: #03050a !important;
    color: #f5f5f7 !important;
}
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background:
        radial-gradient(circle at 12% 0%, rgba(40,92,160,0.18), transparent 30%),
        radial-gradient(circle at 88% 2%, rgba(50,105,190,0.10), transparent 28%),
        linear-gradient(180deg, rgba(255,255,255,0.02), transparent 38%);
    opacity: .9;
}
#MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="stHeader"], [data-testid="collapsedControl"] { display:none!important; visibility:hidden!important; height:0!important; }
.block-container { max-width: 1380px; padding: 4.6rem 3.2rem 3rem !important; position: relative; z-index: 1; }
.hero { display:flex; justify-content:space-between; align-items:flex-start; gap:24px; margin-bottom:2.7rem; }
.title-wrap h1 { margin:0; font-size:2.95rem; line-height:1.04; font-weight:760; letter-spacing:-0.055em; color:#f5f5f7; }
.title-wrap h1 a { color: inherit !important; text-decoration: none !important; }
.title-row { display:flex; align-items:center; gap:14px; }
.status-dot { width:9px; height:9px; border-radius:999px; background:#63f29d; box-shadow:0 0 18px rgba(99,242,157,.42); }
.updated { margin-top:2.1rem; color:#8e8e93; font-size:.76rem; font-weight:760; letter-spacing:.06em; text-transform:uppercase; }
.updated strong { margin-left:8px; color:#b7bcc7; font-family:'DM Mono', monospace; font-weight:500; }
.top-stats { display:flex; align-items:center; gap:12px; color:#8e8e93; font-size:.82rem; margin-top:.35rem; white-space:nowrap; }
.blue-dot { width:8px; height:8px; border-radius:999px; background:#2f70dc; box-shadow:0 0 16px rgba(47,112,220,.45); }
.top-stats strong { color:#f5f5f7; }
.section-label { color:#8e8e93; font-size:.78rem; font-weight:760; letter-spacing:.055em; text-transform:uppercase; margin:1.9rem 0 .85rem; }
.divider { height:1px; background:rgba(255,255,255,.08); margin:2.2rem 0 2rem; }
.summary-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:18px; margin-top:1.1rem; }
.summary-item { border-top:1px solid rgba(255,255,255,.08); padding-top:1.35rem; min-height:105px; }
.summary-item .label { color:#8e8e93; font-size:.75rem; font-weight:760; letter-spacing:.055em; text-transform:uppercase; }
.summary-item .value { margin-top:.5rem; font-family:'DM Mono', monospace; font-size:2.05rem; color:#f5f5f7; line-height:1; }
.summary-item .hint { margin-top:.5rem; color:#777b84; font-size:.82rem; }
.panel-title { display:flex; align-items:center; gap:12px; color:#f5f5f7; font-weight:760; font-size:1.05rem; margin:1.3rem 0 .9rem; }
.chev { color:#f5f5f7; font-size:1.4rem; line-height:1; }
.stage-strip { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin:1rem 0 1.4rem; }
.stage { border:1px solid rgba(255,255,255,.075); border-radius:22px; padding:16px 17px; background:rgba(255,255,255,.022); }
.stage .name { color:#e9ebef; font-weight:760; font-size:.95rem; }
.stage .count { margin-top:.45rem; font-family:'DM Mono', monospace; color:#f5f5f7; font-size:1.45rem; }
.stage .desc { margin-top:.35rem; color:#777b84; font-size:.78rem; }
.calendar-shell { width:100%; max-width:100%; overflow:hidden; }
.calendar-head { display:grid; grid-template-columns:44px minmax(0,1fr) 44px; align-items:center; gap:12px; margin:.2rem 0 .9rem; }
.calendar-title { color:#f5f5f7; font-size:1.08rem; font-weight:760; text-align:center; min-width:0; }
.calendar-nav, .calendar-day { display:flex; align-items:center; justify-content:center; min-height:36px; border-radius:999px; border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.035); color:#f5f5f7!important; font-size:.78rem; font-weight:720; text-decoration:none!important; }
.calendar-nav.disabled { opacity:.34; pointer-events:none; }
.calendar-grid-static { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:8px; margin-bottom:.45rem; max-width:100%; }
.calendar-dow { color:#777b84; text-align:center; font-size:.68rem; font-weight:760; letter-spacing:.05em; text-transform:uppercase; padding:.25rem 0; }
.calendar-empty { min-height:46px; border:1px solid rgba(255,255,255,.045); border-radius:15px; background:rgba(255,255,255,.012); color:rgba(245,245,247,.16); display:flex; align-items:center; justify-content:center; font-family:'DM Mono', monospace; font-size:.8rem; }
.calendar-empty.out { opacity:.28; }
.calendar-day { min-height:46px; border-radius:15px; font-family:'DM Sans', sans-serif; }
.calendar-day.selected { background:#d8dde6; color:#111318!important; border-color:#d8dde6; }
.filter-label { color:#777b84; font-size:.72rem; font-weight:760; letter-spacing:.05em; text-transform:uppercase; margin:0 0 .42rem .15rem; }
.stButton > button, div[data-testid="stDownloadButton"] button { border-radius:999px!important; border:1px solid rgba(255,255,255,.08)!important; background:rgba(255,255,255,.035)!important; color:#f5f5f7!important; min-height:36px!important; padding:0 13px!important; font-size:.78rem!important; font-weight:720!important; font-family:'DM Sans', sans-serif!important; }
.stButton > button[kind="primary"] { background:#d8dde6!important; color:#111318!important; border-color:#d8dde6!important; }
div[data-testid="stDownloadButton"] button { min-height:44px!important; font-size:.82rem!important; margin-top:.8rem!important; }
.signal-table-wrap { margin-top: 1rem; border-top:1px solid rgba(255,255,255,.08); padding-top:1.2rem; overflow-x:auto; }
.signal-table { width:100%; border-collapse:collapse; min-width:980px; font-family:'DM Sans', sans-serif; }
.signal-table thead th { padding:13px 14px; text-align:left; color:#8e8e93; font-size:.72rem; font-weight:760; letter-spacing:.055em; text-transform:uppercase; border-bottom:1px solid rgba(255,255,255,.075); background:#05070d; }
.signal-table tbody td { padding:14px; color:#e9ebef; font-size:.88rem; font-weight:560; border-bottom:1px solid rgba(255,255,255,.055); background:#05070d; vertical-align:middle; }
.signal-table tbody tr:hover td { background:#0b0f18; }
.signal-table .ticker { font-family:'DM Mono', monospace; color:#f5f5f7; font-weight:500; }
.signal-table .num { font-family:'DM Mono', monospace; color:#d7dce5; font-weight:500; white-space:nowrap; }
.signal-table .muted { color:#8e8e93; }
.signal-badge { display:inline-flex; align-items:center; border-radius:999px; padding:5px 10px; font-size:.76rem; font-weight:760; border:1px solid rgba(255,255,255,.09); background:rgba(255,255,255,.045); color:#e9ebef; white-space:nowrap; }
.signal-badge.strong { background:rgba(255,107,122,.12); color:#ffb6bf; border-color:rgba(255,107,122,.22); }
.type-badge { color:#9fb6d9; font-size:.78rem; font-weight:720; }
.puddle-text { color:#b7bcc7; min-width:220px; max-width:330px; line-height:1.34; }
.signal-chart-header { margin-top:1rem; border-top:1px solid rgba(255,255,255,.08); padding-top:1.2rem; }
.signal-chart-title { color:#f5f5f7; font-size:1.05rem; font-weight:760; }
.signal-chart-subtitle { margin-top:.25rem; color:#8e8e93; font-size:.72rem; font-weight:760; letter-spacing:.05em; text-transform:uppercase; }
.signal-chart-note { color:#8e8e93; padding:1rem 0 .2rem; font-size:.86rem; }
.empty-note { color:#8e8e93; padding:1.2rem 0; }
.creator-footer { margin:2.8rem 0 .4rem; }
.creator-footer a { color:rgba(245,245,247,.34); font-family:'DM Sans', sans-serif; font-size:1rem; font-weight:650; text-decoration:none!important; }
.creator-footer a:hover { color:rgba(245,245,247,.58); }
@media (max-width:900px){ .block-container{padding:3.4rem 1.5rem 2.4rem!important;} .hero{display:block;} .top-stats{margin-top:1.2rem;} .summary-grid,.stage-strip{grid-template-columns:repeat(2,minmax(0,1fr));} .title-wrap h1{font-size:2.45rem;} }
@media (max-width:640px){
    .block-container{padding:3.05rem .82rem 2.1rem!important;}
    .summary-grid,.stage-strip{grid-template-columns:1fr;}
    .title-wrap h1{font-size:2.05rem;}
    .calendar-shell{margin-left:-.1rem;margin-right:-.1rem;}
    .calendar-head{grid-template-columns:38px minmax(0,1fr) 38px; gap:6px; margin:.1rem 0 .55rem;}
    .calendar-title{font-size:.98rem;}
    .calendar-nav{min-height:34px; padding:0; font-size:.95rem;}
    .calendar-grid-static{grid-template-columns:repeat(7,minmax(0,1fr)); gap:4px; margin-bottom:.28rem;}
    .calendar-dow{font-size:.58rem; letter-spacing:0; padding:.16rem 0;}
    .calendar-empty,.calendar-day{min-height:34px; border-radius:10px; font-size:.72rem; padding:0;}
    div[data-testid="stElementContainer"]:has(div[data-testid="stPlotlyChart"]),
    .element-container:has(div[data-testid="stPlotlyChart"]){
        height:300px!important;
        min-height:300px!important;
        max-height:300px!important;
        margin-bottom:.15rem!important;
        overflow:hidden!important;
    }
    div[data-testid="stPlotlyChart"]{
        height:300px!important;
        min-height:300px!important;
        max-height:300px!important;
        margin-bottom:0!important;
        padding-bottom:0!important;
        overflow:hidden!important;
    }
    div[data-testid="stDownloadButton"]{margin-top:0!important;}
    div[data-testid="stDownloadButton"] button{margin-top:0!important;}
    .creator-footer{margin:.45rem 0 .15rem;}
    div[data-testid="stPlotlyChart"] > div,
    div[data-testid="stPlotlyChart"] .js-plotly-plot,
    div[data-testid="stPlotlyChart"] .plot-container,
    div[data-testid="stPlotlyChart"] .svg-container,
    div[data-testid="stPlotlyChart"] .main-svg{
        height:300px!important;
        min-height:300px!important;
        max-height:300px!important;
    }
}
</style>
"""

@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def list_scan_files() -> pd.DataFrame:
    remote_rows = []
    try:
        response = requests.get(
            REMOTE_SCAN_API_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "30s-tech-j-streamlit"},
            timeout=12,
        )
        response.raise_for_status()
        for item in response.json():
            filename = str(item.get("name", ""))
            if not filename.startswith("signal_scan_") or not filename.endswith(".csv"):
                continue
            raw = filename.removeprefix("signal_scan_").removesuffix(".csv")
            try:
                scan_date = pd.to_datetime(raw, format="%Y%m%d").date()
            except Exception:
                continue
            download_url = item.get("download_url")
            if download_url:
                remote_rows.append(
                    {
                        "date": scan_date,
                        "path": download_url,
                        "filename": filename,
                        "mtime_ns": item.get("sha", ""),
                    }
                )
        if remote_rows:
            return pd.DataFrame(remote_rows).sort_values("date")
    except Exception:
        pass

    rows = []
    if not SCAN_DIR.exists():
        return pd.DataFrame(columns=["date", "path", "filename"])
    for path in sorted(SCAN_DIR.glob("signal_scan_*.csv")):
        raw = path.stem.replace("signal_scan_", "")
        try:
            scan_date = pd.to_datetime(raw, format="%Y%m%d").date()
        except Exception:
            continue
        rows.append({"date": scan_date, "path": str(path), "filename": path.name, "mtime_ns": path.stat().st_mtime_ns})
    return pd.DataFrame(rows).sort_values("date") if rows else pd.DataFrame(columns=["date", "path", "filename", "mtime_ns"])

@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def load_scan_csv(path: str, mtime_ns: int | None = None) -> pd.DataFrame:
    try:
        if path.startswith("http://") or path.startswith("https://"):
            response = requests.get(path, headers={"User-Agent": "30s-tech-j-streamlit"}, timeout=12)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text))
        else:
            df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    for col in ["price", "price_change_pct", "close", "change_pct", "rsi"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df

def normalize_index_label(value) -> str:
    text = str(value or "").strip()
    normalized = text.replace(" ", "")
    if normalized in {"S&P500,NASDAQ100", "NASDAQ100,S&P500"}:
        return "Dual"
    return text

def parse_stage(puddle) -> str:
    text = str(puddle or "")
    for stage in ["4th", "3rd", "2nd", "1st"]:
        if text.startswith(stage):
            return stage
    return "Other"

def safe_num(value, suffix="") -> str:
    try:
        return f"{float(value):.2f}{suffix}"
    except Exception:
        return "--"

def safe_text(value, fallback="--") -> str:
    if value is None or pd.isna(value):
        return fallback
    text = str(value).strip()
    return text if text and text.lower() != "nan" else fallback

def central_time_label(value) -> str:
    try:
        timestamp = pd.to_datetime(value, errors="raise")
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(CENTRAL_TZ)
        else:
            timestamp = timestamp.tz_convert(CENTRAL_TZ)
        return timestamp.strftime("%H:%M CT")
    except Exception:
        return "--"

def first_non_null(row: pd.Series, keys: list[str]):
    for key in keys:
        value = row.get(key)
        if value is not None and not pd.isna(value):
            return value
    return None

def yahoo_symbol(ticker: str) -> str:
    return str(ticker or "").strip().upper().replace(".", "-")

def normalize_date_column(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty or "Date" not in data.columns:
        return data
    data = data.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    return data.dropna(subset=["Date"]).sort_values("Date").drop_duplicates("Date").reset_index(drop=True)

def padded_values(values, length: int):
    values = values or []
    return list(values) + [None] * max(0, length - len(values))

@st.cache_data(show_spinner=False, ttl=CHART_CACHE_TTL_SECONDS)
def fetch_yahoo_chart(symbol: str, period: str = "2y") -> pd.DataFrame:
    encoded_symbol = quote(yahoo_symbol(symbol), safe="")
    if not encoded_symbol:
        return pd.DataFrame()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_symbol}"
    params = {
        "range": period,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    try:
        response = requests.get(
            url,
            params=params,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return pd.DataFrame()

    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result or not result.get("timestamp"):
        return pd.DataFrame()

    timestamps = result.get("timestamp") or []
    quote_data = (result.get("indicators", {}).get("quote") or [{}])[0]
    length = len(timestamps)
    dates = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None).normalize()
    data = pd.DataFrame({
        "Date": dates,
        "Open": padded_values(quote_data.get("open"), length)[:length],
        "High": padded_values(quote_data.get("high"), length)[:length],
        "Low": padded_values(quote_data.get("low"), length)[:length],
        "Close": padded_values(quote_data.get("close"), length)[:length],
        "Volume": padded_values(quote_data.get("volume"), length)[:length],
    })
    data = data.dropna(subset=["Close"])
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    return normalize_date_column(data)

def calculate_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    if len(data) < window:
        return pd.Series([pd.NA] * len(data), index=data.index, dtype="float64")
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).round(2)

def calculate_moving_averages(data: pd.DataFrame, windows: list[int] | None = None) -> pd.DataFrame:
    data = data.copy()
    for window in windows or [20, 60, 120, 200]:
        data[f"MA{window}"] = data["Close"].rolling(window=window).mean().round(2) if len(data) >= window else pd.NA
    return data

def generate_puddle_signals(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    alerts = [""]
    for index in range(1, len(data)):
        row = data.iloc[index]
        prev = data.iloc[index - 1]
        conditions = {
            1: (
                pd.notna(row.get("MA20"))
                and pd.notna(prev.get("MA20"))
                and row["Close"] < row["MA20"]
                and prev["Close"] >= prev.get("MA20", pd.NA)
            ),
            2: (
                pd.notna(row.get("MA60"))
                and pd.notna(prev.get("MA60"))
                and row["Close"] < row["MA60"]
                and prev["Close"] >= prev.get("MA60", pd.NA)
            ),
            3: (
                pd.notna(row.get("MA120"))
                and pd.notna(prev.get("MA120"))
                and row["Close"] < row["MA120"]
                and prev["Close"] >= prev.get("MA120", pd.NA)
            ),
            4: (
                pd.notna(row.get("MA200"))
                and pd.notna(prev.get("MA200"))
                and row["Close"] < row["MA200"]
                and prev["Close"] >= prev.get("MA200", pd.NA)
                and pd.notna(row.get("RSI"))
                and row["RSI"] < 30
            ),
        }
        timings = [stage for stage, matched in conditions.items() if matched]
        alerts.append({
            4: "4th: MA200, RSI<=30, 100% cash, 40d",
            3: "3rd: MA120, 50% cash, 5d",
            2: "2nd: MA60, 50% cash, 5d",
            1: "1st: MA20, 10% cash",
        }.get(max(timings), "") if timings else "")
    data["Puddle"] = alerts
    return data

@st.cache_data(show_spinner=False, ttl=CHART_CACHE_TTL_SECONDS)
def fetch_market_overlay(period: str = "2y") -> pd.DataFrame:
    vix = fetch_yahoo_chart("^VIX", period)
    vix1d = fetch_yahoo_chart("^VIX1D", period)
    if vix.empty or vix1d.empty:
        return pd.DataFrame(columns=["Date", "VIX", "VIX1D", "VIX1D>VIX"])

    overlay = pd.merge(
        vix[["Date", "Close"]].rename(columns={"Close": "VIX"}),
        vix1d[["Date", "Close"]].rename(columns={"Close": "VIX1D"}),
        on="Date",
        how="outer",
    )
    overlay["VIX1D>VIX"] = (
        overlay["VIX"].notna()
        & overlay["VIX1D"].notna()
        & (overlay["VIX"] >= 25)
        & (overlay["VIX1D"] > overlay["VIX"])
    )
    return normalize_date_column(overlay)

@st.cache_data(show_spinner=False, ttl=CHART_CACHE_TTL_SECONDS)
def load_signal_history(ticker: str) -> pd.DataFrame:
    data = fetch_yahoo_chart(ticker, "2y")
    if data.empty:
        return pd.DataFrame()

    data[["Close", "Open", "High", "Low"]] = data[["Close", "Open", "High", "Low"]].round(2)
    data = calculate_moving_averages(data)
    data["RSI"] = calculate_rsi(data)
    data = generate_puddle_signals(data)

    overlay = fetch_market_overlay("2y")
    if not overlay.empty:
        data = pd.merge(data, overlay, on="Date", how="left")
    else:
        data["VIX1D>VIX"] = False

    latest_date = data["Date"].max()
    data = data[data["Date"] >= latest_date - pd.Timedelta(days=365)].reset_index(drop=True)
    return data

def has_text_signal(value) -> bool:
    return bool(str(value or "").strip())

def build_signal_chart(data: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=data["Close"],
        name="Price",
        mode="lines",
        line={"color": "#f5f5f7", "width": 2.2},
        hovertemplate="%{x|%Y-%m-%d}<br>Price %{y:.2f}<extra></extra>",
    ))

    ma_styles = {
        "MA20": "#5aa6ff",
        "MA60": "#f0c35a",
        "MA120": "#e6829a",
    }
    for ma, color in ma_styles.items():
        if ma in data.columns and data[ma].notna().any():
            fig.add_trace(go.Scatter(
                x=data["Date"],
                y=data[ma],
                name=ma,
                mode="lines",
                line={"color": color, "width": 1.4, "dash": "dot"},
                hovertemplate=f"%{{x|%Y-%m-%d}}<br>{ma} %{{y:.2f}}<extra></extra>",
            ))

    fig.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode="lines",
        name="VIX1D > VIX",
        line={"color": "rgba(47,128,255,0.62)", "width": 1.8},
        hoverinfo="skip",
    ))
    if "VIX1D>VIX" in data.columns:
        for signal_date in data.loc[data["VIX1D>VIX"].fillna(False), "Date"]:
            fig.add_vline(
                x=signal_date,
                line={"color": "rgba(47,128,255,0.46)", "width": 1.5},
                layer="below",
            )

    signal_mask = data["RSI"].le(30) & data["Puddle"].apply(has_text_signal)
    signal_points = data[signal_mask]
    fig.add_trace(go.Scatter(
        x=signal_points["Date"] if not signal_points.empty else [None],
        y=signal_points["Close"] if not signal_points.empty else [None],
        mode="markers",
        name="RSI & Puddle",
        marker={"symbol": "circle", "size": 8, "color": "#2F80FF", "line": {"width": 1.5, "color": "white"}},
        hovertemplate="%{x|%Y-%m-%d}<br>RSI & Puddle<br>Price %{y:.2f}<extra></extra>",
    ))

    fig.update_layout(
        title={"text": ""},
        height=430,
        margin={"l": 12, "r": 12, "t": 34, "b": 28},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#05070d",
        font={"family": "DM Sans, sans-serif", "color": "#d7dce5", "size": 11},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.03,
            "xanchor": "right",
            "x": 1,
            "font": {"color": "#d7dce5", "size": 11},
        },
        hovermode="x unified",
        dragmode=False,
    )
    fig.update_xaxes(
        tickformat="%y.%m",
        dtick="M2",
        showgrid=True,
        gridcolor="rgba(255,255,255,0.055)",
        zeroline=False,
        fixedrange=True,
        tickfont={"color": "rgba(245,245,247,0.54)", "size": 10},
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.075)",
        zeroline=False,
        fixedrange=True,
        tickfont={"color": "rgba(245,245,247,0.46)", "size": 10},
    )
    return fig

def calendar_weeks(selected_month):
    cal = Calendar(firstweekday=6)
    yield from cal.monthdatescalendar(selected_month.year, selected_month.month)

def render_calendar_header() -> str:
    cells = [f"<div class='calendar-dow'>{day}</div>" for day in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]]
    return f"<div class='calendar-grid-static'>{''.join(cells)}</div>"

def parse_calendar_component_value(value) -> tuple:
    if not isinstance(value, dict):
        return None, None
    try:
        selected_date = pd.to_datetime(value.get("date")).date() if value.get("date") else None
        current_month = pd.to_datetime(f"{value.get('month')}-01").date() if value.get("month") else None
    except Exception:
        return None, None
    return selected_date, current_month

def calendar_link(date_value, month_value) -> str:
    return f"/?date={date_value.isoformat()}&month={month_value:%Y-%m}"

def render_calendar_nav(current_month, selected_date, month_options: list) -> str:
    current_idx = month_options.index(current_month)
    prev_month = month_options[current_idx - 1] if current_idx > 0 else None
    next_month = month_options[current_idx + 1] if current_idx < len(month_options) - 1 else None
    prev_href = calendar_link(selected_date, prev_month) if prev_month else "#"
    next_href = calendar_link(selected_date, next_month) if next_month else "#"
    prev_class = "calendar-nav" if prev_month else "calendar-nav disabled"
    next_class = "calendar-nav" if next_month else "calendar-nav disabled"
    return (
        "<div class='calendar-head'>"
        f"<a class='{prev_class}' href='{prev_href}' target='_self' aria-label='Previous month'>‹</a>"
        f"<div class='calendar-title'>{month_name[current_month.month]} {current_month.year}</div>"
        f"<a class='{next_class}' href='{next_href}' target='_self' aria-label='Next month'>›</a>"
        "</div>"
    )

def render_empty_calendar_cell(day, selected_month) -> str:
    classes = ["calendar-empty"]
    if day.month != selected_month.month:
        classes.append("out")
    text = day.day if day.month == selected_month.month else ""
    return f"<div class='{' '.join(classes)}'>{text}</div>"

def render_calendar_grid(current_month, selected_date, available_dates: set) -> str:
    cells = [render_calendar_header()]
    for week in calendar_weeks(current_month):
        day_cells = []
        for day in week:
            if day in available_dates:
                selected_class = " selected" if day == selected_date else ""
                day_cells.append(
                    f"<a class='calendar-day{selected_class}' href='{calendar_link(day, current_month)}' target='_self'>{day.day}</a>"
                )
            else:
                day_cells.append(render_empty_calendar_cell(day, current_month))
        cells.append(f"<div class='calendar-grid-static'>{''.join(day_cells)}</div>")
    return "<div class='calendar-shell'>" + "".join(cells) + "</div>"

def render_calendar_component(current_month, selected_date, available_dates: set, month_options: list):
    current_idx = month_options.index(current_month)
    weeks = []
    for week in calendar_weeks(current_month):
        week_cells = []
        for day in week:
            week_cells.append({
                "date": day.isoformat(),
                "label": str(day.day),
                "available": day in available_dates,
                "in_month": day.month == current_month.month,
            })
        weeks.append(week_cells)
    return calendar_component(
        title=f"{month_name[current_month.month]} {current_month.year}",
        current_month=f"{current_month:%Y-%m}",
        selected_date=selected_date.isoformat(),
        prev_month=f"{month_options[current_idx - 1]:%Y-%m}" if current_idx > 0 else None,
        next_month=f"{month_options[current_idx + 1]:%Y-%m}" if current_idx < len(month_options) - 1 else None,
        weeks=weeks,
        default=None,
        key="calendar_picker",
    )

def first_query_value(key: str) -> str | None:
    value = st.query_params.get(key)
    if isinstance(value, list):
        return value[0] if value else None
    return value

def prepare_signal_table_rows(df: pd.DataFrame) -> list[dict]:
    rows = []
    for _, row in df.iterrows():
        company = str(row.get("company_name", "") or "")
        rows.append({
            "asset_type": str(row.get("asset_type", "") or ""),
            "index": normalize_index_label(row.get("universe", "")),
            "rank": safe_text(row.get("rank", "")),
            "ticker": str(row.get("ticker", "") or ""),
            "company": company if company.strip() else "--",
            "signal": str(row.get("signal", "") or ""),
            "price": safe_num(first_non_null(row, ["price", "close"])),
            "change": safe_num(first_non_null(row, ["price_change_pct", "change_pct"]), "%"),
            "rsi": safe_num(row.get("rsi")),
            "puddle": str(row.get("puddle", "") or ""),
        })
    return rows

def parse_signal_table_value(value) -> tuple[str | None, str | None]:
    if not isinstance(value, dict):
        return None, None
    ticker = str(value.get("ticker") or "").strip().upper()
    signal = str(value.get("signal") or "").strip()
    return (ticker or None), (signal or None)

def render_signal_table_component(df: pd.DataFrame, selected_ticker: str | None):
    return signal_table_component(
        rows=prepare_signal_table_rows(df),
        selected_ticker=selected_ticker or "",
        default=None,
        key="signal_table_picker",
    )

def render_signal_chart_section(ticker: str, signal: str, company: str | None = None) -> None:
    title = f"{ticker} Signals"
    subtitle_parts = [signal or "Signal", "1Y Trend"]
    if company and company != "--":
        subtitle_parts.insert(0, company)
    st.markdown(
        "<div class='signal-chart-header'>"
        f"<div class='signal-chart-title'>{escape(title)}</div>"
        f"<div class='signal-chart-subtitle'>{escape(' · '.join(subtitle_parts))}</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    with st.spinner(f"Loading {ticker} signal chart..."):
        history = load_signal_history(ticker)
    if history.empty:
        st.markdown(
            f"<div class='signal-chart-note'>Could not load chart data for {escape(ticker)}.</div>",
            unsafe_allow_html=True,
        )
        return
    st.plotly_chart(
        build_signal_chart(history, ticker),
        use_container_width=True,
        config={"displayModeBar": False, "responsive": True},
    )

def chip_filter(label: str, options: list[str], key: str) -> str:
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = options[0]
    st.markdown(f"<div class='filter-label'>{label}</div>", unsafe_allow_html=True)
    cols = st.columns([1] * len(options), gap="small")
    for idx, option in enumerate(options):
        with cols[idx]:
            if st.button(option, key=f"{key}-{option}", type="primary" if st.session_state[key] == option else "secondary"):
                st.session_state[key] = option
                st.rerun()
    return st.session_state[key]

def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    file_df = list_scan_files()
    if file_df.empty:
        st.markdown("<div class='title-wrap'><h1><a href='?dashboard=us' target='_self'>Puddle Signal Scanner</a></h1></div>", unsafe_allow_html=True)
        st.info("signal_scans 폴더에 CSV가 아직 없습니다.")
        return

    latest_date = file_df["date"].max()
    available_dates = set(file_df["date"].tolist())
    calendar_selected_date, calendar_month = parse_calendar_component_value(st.session_state.get("calendar_picker"))
    query_date = first_query_value("date")
    if calendar_selected_date:
        selected_date = calendar_selected_date
    elif query_date:
        try:
            selected_date = pd.to_datetime(query_date).date()
        except Exception:
            selected_date = st.session_state.get("selected_scan_date", latest_date)
    elif "selected_scan_date" not in st.session_state:
        selected_date = latest_date
    else:
        selected_date = st.session_state.selected_scan_date
    if selected_date not in set(file_df["date"].tolist()):
        selected_date = latest_date
        st.session_state.selected_scan_date = latest_date
    else:
        st.session_state.selected_scan_date = selected_date

    month_options = sorted({d.replace(day=1) for d in file_df["date"]})
    query_month = first_query_value("month")
    if calendar_month:
        current_month = calendar_month
    elif query_month:
        try:
            current_month = pd.to_datetime(f"{query_month}-01").date()
        except Exception:
            current_month = selected_date.replace(day=1)
    else:
        current_month = selected_date.replace(day=1)
    if current_month not in month_options:
        current_month = selected_date.replace(day=1)

    selected_row = file_df[file_df["date"] == selected_date].iloc[-1]
    df = load_scan_csv(selected_row["path"], int(selected_row.get("mtime_ns", 0)))

    scan_time = "--"
    for timestamp_col in ["scan_timestamp_ct", "scan_timestamp_utc"]:
        if not df.empty and timestamp_col in df.columns:
            times = df[timestamp_col].dropna()
            if not times.empty:
                scan_time = central_time_label(times.iloc[0])
                break

    total = len(df)
    rsi_puddle = int((df.get("signal") == "RSI & Puddle").sum()) if not df.empty and "signal" in df.columns else 0
    stocks = int((df.get("asset_type") == "Stock").sum()) if not df.empty and "asset_type" in df.columns else 0
    etfs = int((df.get("asset_type") == "ETF").sum()) if not df.empty and "asset_type" in df.columns else 0

    st.markdown(f"""
    <div class='hero'>
      <div class='title-wrap'>
        <div class='title-row'><span class='status-dot'></span><h1><a href='?dashboard=us' target='_self'>Puddle Signal Scanner</a></h1></div>
        <div class='updated'>UPDATED <strong>{scan_time}</strong></div>
      </div>
      <div class='top-stats'><span class='blue-dot'></span><span>Selected <strong>{selected_date}</strong></span><span>·</span><span>Total <strong>{total}</strong></span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='section-label'>Saved dates</div>", unsafe_allow_html=True)
    render_calendar_component(current_month, selected_date, available_dates, month_options)

    st.markdown("<div class='summary-grid'>" +
        f"<div class='summary-item'><div class='label'>Signals</div><div class='value'>{total}</div><div class='hint'>Puddle + RSI & Puddle</div></div>" +
        f"<div class='summary-item'><div class='label'>RSI & Puddle</div><div class='value'>{rsi_puddle}</div><div class='hint'>stronger warning</div></div>" +
        f"<div class='summary-item'><div class='label'>Stocks</div><div class='value'>{stocks}</div><div class='hint'>S&P500 + NASDAQ100</div></div>" +
        f"<div class='summary-item'><div class='label'>ETFs</div><div class='value'>{etfs}</div><div class='hint'>representative set</div></div>" +
        "</div>", unsafe_allow_html=True)

    if not df.empty:
        df["_stage"] = df.get("puddle", pd.Series(dtype=str)).apply(parse_stage)
        counts = df["_stage"].value_counts().to_dict()
        st.markdown("<div class='panel-title'><span class='chev'>›</span><span>Puddle Overview</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='stage-strip'>" +
            f"<div class='stage'><div class='name'>1st · MA20</div><div class='count'>{counts.get('1st',0)}</div><div class='desc'>short-term break</div></div>" +
            f"<div class='stage'><div class='name'>2nd · MA60</div><div class='count'>{counts.get('2nd',0)}</div><div class='desc'>mid-term break</div></div>" +
            f"<div class='stage'><div class='name'>3rd · MA120</div><div class='count'>{counts.get('3rd',0)}</div><div class='desc'>longer trend warning</div></div>" +
            f"<div class='stage'><div class='name'>4th · MA200</div><div class='count'>{counts.get('4th',0)}</div><div class='desc'>MA200 + RSI</div></div>" +
            "</div>", unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Filter</div>", unsafe_allow_html=True)
    filter_cols = st.columns([1.2, 1.8, 3.4])
    with filter_cols[0]:
        type_filter = chip_filter("Type", ["Stock", "ETF"], "type_filter")
    with filter_cols[1]:
        signal_filter = chip_filter("Signal", ["RSI & Puddle", "Puddle"], "signal_filter")

    filtered = df.copy()
    if "asset_type" in filtered.columns:
        filtered = filtered[filtered["asset_type"] == type_filter]
    if "signal" in filtered.columns:
        if signal_filter == "Puddle":
            filtered = filtered[filtered.get("puddle", pd.Series(dtype=str)).apply(has_text_signal)]
        else:
            filtered = filtered[filtered["signal"] == signal_filter]

    st.markdown("<div class='panel-title'><span class='chev'>›</span><span>Signal List</span></div>", unsafe_allow_html=True)
    clicked_ticker, _ = parse_signal_table_value(st.session_state.get("signal_table_picker"))
    available_tickers = set(filtered.get("ticker", pd.Series(dtype=str)).astype(str).str.upper())
    selected_chart_ticker = clicked_ticker if clicked_ticker in available_tickers else None
    render_signal_table_component(filtered, selected_chart_ticker)
    if selected_chart_ticker:
        chart_row = filtered[filtered["ticker"].astype(str).str.upper() == selected_chart_ticker].iloc[0]
        render_signal_chart_section(
            selected_chart_ticker,
            str(chart_row.get("signal", "")),
            str(chart_row.get("company_name", "")),
        )
    st.download_button("Download selected CSV", data=filtered.drop(columns=["_stage"], errors="ignore").to_csv(index=False).encode("utf-8"), file_name=selected_row["filename"], mime="text/csv", use_container_width=True)
    st.markdown(f"<div class='creator-footer'><a href='{THREADS_URL}' target='_blank' rel='noopener'>by 30s_tech_j</a></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
