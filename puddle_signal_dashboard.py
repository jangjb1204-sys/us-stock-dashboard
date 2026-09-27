from __future__ import annotations

import json
import re
from calendar import Calendar
from concurrent.futures import ThreadPoolExecutor
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

import ui_theme as ui
from stock_analyzer import (
    calculate_moving_averages,
    calculate_rsi,
    generate_puddle_signals,
    puddle_label_ko,
)


APP_DIR = Path(__file__).resolve().parent
SCAN_DIR = APP_DIR / "signal_scans"
REMOTE_SCAN_INDEX_URL = "https://raw.githubusercontent.com/jangjb1204-sys/puddle-signal-dashboard/main/signal_scans/index.json"
REMOTE_SCAN_API_URL = "https://api.github.com/repos/jangjb1204-sys/puddle-signal-dashboard/contents/signal_scans?ref=main"
CENTRAL_TZ = ZoneInfo("America/Chicago")
CACHE_TTL_SECONDS = 60
CHART_CACHE_TTL_SECONDS = 60 * 60 * 6
calendar_component = components.declare_component("puddle_calendar", path=str(APP_DIR / "calendar_component"))
signal_table_component = components.declare_component("puddle_signal_table", path=str(APP_DIR / "signal_table_component"))

# Page-only pieces; the shared look (background, fonts, header, pills, tabs,
# buttons, stats row, footer) comes from ui_theme.BASE_CSS.
CSS = ui.html(f"""
<style>
.panel-title {{ display:flex; align-items:center; gap:10px; color:{ui.TEXT}; font-weight:650; font-size:1.02rem; margin:2.2rem 0 .9rem; }}
.chev {{ color:{ui.FAINT}; font-size:1.3rem; line-height:1; }}
.stage-strip {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(104px,1fr)); gap:8px; margin:1.1rem 0 0; }}
.pd-stats {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); column-gap:28px; row-gap:18px; }}
.pd-stats .tj-stat {{ padding-top:18px; }}
.pd-open {{ display:inline-block; margin-top:.9rem; color:rgba(255,255,255,.72)!important; font-size:.84rem; font-weight:600; text-decoration:none!important; }}
.pd-open:hover {{ color:#F2F5F8!important; }}
.stage {{ border:1px solid rgba(255,255,255,.05); border-radius:12px; padding:10px 12px; background:rgba(255,255,255,.035); min-width:0; }}
.stage .name {{ color:rgba(255,255,255,.82); font-weight:620; font-size:.86rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.stage .name span {{ color:rgba(255,255,255,.46); font-weight:520; font-size:.76rem; margin-left:2px; }}
.stage .count {{ margin-top:.25rem; font-variant-numeric:tabular-nums; color:{ui.TEXT}; font-size:1.26rem; font-weight:620; }}
.stage .desc {{ margin-top:.3rem; color:rgba(255,255,255,.46); font-size:.78rem; }}
.calendar-shell {{ width:100%; max-width:100%; overflow:hidden; }}
.calendar-head {{ display:grid; grid-template-columns:44px minmax(0,1fr) 44px; align-items:center; gap:12px; margin:.2rem 0 .9rem; }}
.calendar-title {{ color:{ui.TEXT}; font-size:1.02rem; font-weight:650; text-align:center; min-width:0; }}
.calendar-nav, .calendar-day {{ display:flex; align-items:center; justify-content:center; min-height:36px; border-radius:999px; border:1px solid rgba(255,255,255,.05); background:rgba(255,255,255,.035); color:{ui.TEXT}!important; font-size:.78rem; font-weight:620; text-decoration:none!important; }}
.calendar-nav.disabled {{ opacity:.34; pointer-events:none; }}
.calendar-grid-static {{ display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:8px; margin-bottom:.45rem; max-width:100%; }}
.calendar-dow {{ color:rgba(255,255,255,.46); text-align:center; font-size:12px; font-weight:500; letter-spacing:.035em; text-transform:uppercase; padding:.25rem 0; }}
.calendar-empty {{ min-height:46px; border:1px solid rgba(255,255,255,.035); border-radius:12px; background:rgba(255,255,255,.012); color:rgba(255,255,255,.18); display:flex; align-items:center; justify-content:center; font-size:.8rem; }}
.calendar-empty.out {{ opacity:.28; }}
.calendar-day {{ min-height:46px; border-radius:12px; }}
.calendar-day.selected {{ background:rgba(242,245,248,.76); color:{ui.BG}!important; border-color:rgba(242,245,248,.54); }}
.filter-label {{ color:rgba(255,255,255,.46); font-size:12px; font-weight:500; letter-spacing:.035em; text-transform:uppercase; margin:0 0 .42rem .15rem; }}
.divider {{ height:1px; background:rgba(255,255,255,.055); margin:2.15rem 0 1.6rem; }}
.signal-chart-header {{ margin-top:1.4rem; padding-top:1.2rem; border-top:1px solid {ui.LINE}; }}
.signal-chart-title {{ color:{ui.TEXT}; font-size:1.02rem; font-weight:650; }}
.signal-chart-subtitle {{ margin-top:.25rem; color:rgba(255,255,255,.46); font-size:12px; font-weight:500; letter-spacing:.035em; text-transform:uppercase; }}
.signal-chart-note, .empty-note {{ color:rgba(255,255,255,.46); padding:1rem 0 .2rem; font-size:.86rem; }}
div[data-testid="stDownloadButton"] {{ margin-top:1rem; }}
@media (max-width:640px) {{
    .calendar-head {{ grid-template-columns:38px minmax(0,1fr) 38px; gap:6px; margin:.1rem 0 .55rem; }}
    .calendar-grid-static {{ gap:4px; margin-bottom:.28rem; }}
    .calendar-dow {{ font-size:.58rem; letter-spacing:0; padding:.16rem 0; }}
    .calendar-empty, .calendar-day {{ min-height:34px; border-radius:10px; font-size:.72rem; padding:0; }}
    div[data-testid="stElementContainer"]:has(div[data-testid="stPlotlyChart"]),
    .element-container:has(div[data-testid="stPlotlyChart"]),
    div[data-testid="stPlotlyChart"],
    div[data-testid="stPlotlyChart"] > div,
    div[data-testid="stPlotlyChart"] .js-plotly-plot,
    div[data-testid="stPlotlyChart"] .plot-container,
    div[data-testid="stPlotlyChart"] .svg-container,
    div[data-testid="stPlotlyChart"] .main-svg {{ height:300px!important; min-height:300px!important; max-height:300px!important; overflow:hidden!important; }}
}}
</style>
""")

@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def list_scan_files() -> pd.DataFrame:
    index_rows = []
    try:
        response = requests.get(REMOTE_SCAN_INDEX_URL, headers={"User-Agent": "30s-tech-j-streamlit"}, timeout=12)
        response.raise_for_status()
        for item in json.loads(response.text):
            try:
                scan_date = pd.to_datetime(item.get("date"), format="%Y-%m-%d").date()
            except Exception:
                continue
            path = item.get("url")
            filename = item.get("filename")
            if path and filename:
                index_rows.append(
                    {
                        "date": scan_date,
                        "path": path,
                        "filename": filename,
                        "mtime_ns": item.get("mtime_ns", ""),
                    }
                )
        if index_rows:
            return pd.DataFrame(index_rows).sort_values("date")
    except Exception:
        pass

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

def count_scan_rows(path: str) -> int | None:
    try:
        if path.startswith(("http://", "https://")):
            response = requests.get(path, headers={"User-Agent": "30s-tech-j-streamlit"}, timeout=12)
            response.raise_for_status()
            return len(pd.read_csv(StringIO(response.text)))
        return len(pd.read_csv(path))
    except Exception:
        return None

@st.cache_data(show_spinner=False, ttl=CHART_CACHE_TTL_SECONDS)
def load_scan_counts(files: tuple[tuple[str, str, str], ...]) -> dict[str, int | None]:
    """Signal count for each (date, path, version) — one month's scans, fetched in parallel."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        counts = list(pool.map(lambda item: count_scan_rows(item[1]), files))
    return {item[0]: count for item, count in zip(files, counts)}

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

def scan_time_label(value) -> str:
    """When the scan ran, in Korean time (naive stamps are Chicago time)."""
    return ui.kst_time(value, tz=CENTRAL_TZ) or "--"

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
        name="가격",
        mode="lines",
        line={"color": "#f5f5f7", "width": 2.2},
        hovertemplate="%{x|%Y-%m-%d}<br>가격 %{y:.2f}<extra></extra>",
    ))

    ma_styles = {
        "MA20": "#4C8DF0",
        "MA60": "#BA852B",
        "MA120": "#B8649E",
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
        name="RSI+Puddle",
        marker={"symbol": "circle", "size": 8, "color": "#2F80FF", "line": {"width": 1.5, "color": "white"}},
        hovertemplate="%{x|%Y-%m-%d}<br>RSI+Puddle<br>가격 %{y:.2f}<extra></extra>",
    ))

    fig.update_layout(
        title={"text": ""},
        height=430,
        margin={"l": 12, "r": 12, "t": 34, "b": 28},
        **ui.PLOT_LAYOUT,
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
        f"<div class='calendar-title'>{current_month.year}년 {current_month.month}월</div>"
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

def render_calendar_component(current_month, selected_date, available_dates: set, month_options: list,
                              counts: dict | None = None):
    counts = counts or {}
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
                "count": counts.get(day.isoformat()),
            })
        weeks.append(week_cells)
    return calendar_component(
        title=f"{current_month.year}년 {current_month.month}월",
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

SIGNAL_LABEL = {"RSI & Puddle": "RSI+Puddle", "Puddle": "Puddle"}

def prepare_signal_table_rows(df: pd.DataFrame) -> list[dict]:
    rows = []
    for _, row in df.iterrows():
        company = str(row.get("company_name", "") or "")
        universe = normalize_index_label(row.get("universe", ""))
        rank = safe_text(row.get("rank", ""), "")
        dual = re.fullmatch(r"S(\d+)/N(\d+)", rank)
        if universe == "Dual" and dual:
            meta = f"S&P500 {dual.group(1)}위 · NASDAQ100 {dual.group(2)}위"
        elif universe == "Dual":
            meta = "S&P500 · NASDAQ100"
        else:
            meta = f"{universe} 안 {rank}위" if rank and universe else universe
        signal = str(row.get("signal", "") or "")
        rows.append({
            "meta": meta,
            "signal_label": SIGNAL_LABEL.get(signal, signal),
            "asset_type": str(row.get("asset_type", "") or ""),
            "index": normalize_index_label(row.get("universe", "")),
            "rank": safe_text(row.get("rank", "")),
            "ticker": str(row.get("ticker", "") or ""),
            "company": company if company.strip() else "--",
            "signal": str(row.get("signal", "") or ""),
            "price": safe_num(first_non_null(row, ["price", "close"])),
            "change": safe_num(first_non_null(row, ["price_change_pct", "change_pct"]), "%"),
            "rsi": safe_num(row.get("rsi")),
            "puddle": puddle_label_ko(row.get("puddle", "")),
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
    title = f"{ticker} 신호 차트"
    subtitle_parts = [SIGNAL_LABEL.get(signal, signal) or "신호", "최근 1년"]
    if company and company != "--":
        subtitle_parts.insert(0, company)
    st.markdown(
        "<div class='signal-chart-header'>"
        f"<div class='signal-chart-title'>{escape(title)}</div>"
        f"<div class='signal-chart-subtitle'>{escape(' · '.join(subtitle_parts))}</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    with st.spinner(f"{ticker} 불러오는 중"):
        history = load_signal_history(ticker)
    if history.empty:
        st.markdown(
            f"<div class='signal-chart-note'>{escape(ticker)} 차트 데이터 없음</div>",
            unsafe_allow_html=True,
        )
        return
    st.plotly_chart(
        build_signal_chart(history, ticker),
        use_container_width=True,
        config={"displayModeBar": False, "responsive": True},
    )
    st.markdown(
        f"<a class='pd-open' href='?dashboard=us&amp;ticker={quote(ticker)}' target='_self'>"
        f"미국 시장에서 {escape(ticker)} 보기 →</a>",
        unsafe_allow_html=True,
    )

def chip_filter(label: str, options: list[str], key: str, labels: dict | None = None) -> str:
    """Pill buttons; `labels` maps each option to its text (with a count)."""
    labels = labels or {}
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = options[0]
    st.markdown(f"<div class='filter-label'>{label}</div>", unsafe_allow_html=True)
    cols = st.columns([1] * len(options), gap="small")
    for idx, option in enumerate(options):
        with cols[idx]:
            if st.button(labels.get(option, option), key=f"{key}-{option}", type="primary" if st.session_state[key] == option else "secondary"):
                st.session_state[key] = option
                st.rerun()
    return st.session_state[key]

def main() -> None:
    st.markdown(ui.BASE_CSS, unsafe_allow_html=True)
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(ui.nav_html("puddle"), unsafe_allow_html=True)
    file_df = list_scan_files()
    if file_df.empty:
        st.markdown(ui.hero_html("Puddle Signal Scanner", dot="closed", self_key="puddle"), unsafe_allow_html=True)
        st.info("signal_scans 폴더에 CSV가 아직 없습니다.")
        st.markdown(ui.footer_html(), unsafe_allow_html=True)
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
            selected_date = latest_date
    else:
        selected_date = latest_date
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
    df = load_scan_csv(str(selected_row["path"]), selected_row.get("mtime_ns"))

    scan_time = "--"
    for timestamp_col in ["scan_timestamp_ct", "scan_timestamp_utc"]:
        if not df.empty and timestamp_col in df.columns:
            times = df[timestamp_col].dropna()
            if not times.empty:
                scan_time = scan_time_label(times.iloc[0])
                break

    total = len(df)
    rsi_puddle = int((df.get("signal") == "RSI & Puddle").sum()) if not df.empty and "signal" in df.columns else 0
    stocks = int((df.get("asset_type") == "Stock").sum()) if not df.empty and "asset_type" in df.columns else 0
    etfs = int((df.get("asset_type") == "ETF").sum()) if not df.empty and "asset_type" in df.columns else 0

    right = (f"<span class='tj-dot'></span><span>선택 <strong>{escape(ui.kdate(selected_date))}</strong></span>"
             f"<span>·</span><span>신호 <strong>{total}</strong>개</span>")
    st.markdown(ui.hero_html("Puddle Signal Scanner", f"{scan_time} 스캔" if scan_time != "--" else None,
                             dot="open", right=right, self_key="puddle"), unsafe_allow_html=True)

    # Summary first (left), calendar beside it (right); on a phone the summary
    # comes first, so the day's result is visible without scrolling past a month.
    month_files = tuple(
        (row["date"].isoformat(), str(row["path"]), str(row.get("mtime_ns", "")))
        for _, row in file_df.iterrows() if row["date"].replace(day=1) == current_month
    )
    counts = load_scan_counts(month_files)
    counts[selected_date.isoformat()] = total
    stage_counts = {}
    if not df.empty:
        df["_stage"] = df.get("puddle", pd.Series(dtype=str)).apply(parse_stage)
        stage_counts = df["_stage"].value_counts().to_dict()

    summary_col, calendar_col = st.columns([1, 1.05], gap="large")
    with summary_col:
        st.markdown(f"<div class='tj-label'>{escape(ui.kdate(selected_date))} 스캔 결과</div>", unsafe_allow_html=True)
        stats = [
            ("전체 신호", total, "", "Puddle + RSI+Puddle"),
            ("RSI+Puddle", rsi_puddle, "", "과매도 동반"),
            ("주식", stocks, "", "S&amp;P500 + NASDAQ100"),
            ("ETF", etfs, "", "대표 ETF"),
        ]
        stages = [("1차", "MA20", "1st"), ("2차", "MA60", "2nd"), ("3차", "MA120", "3rd"), ("4차", "MA200", "4th")]
        st.markdown(
            "<div class='pd-stats'>" + "".join(
                f"<div class='tj-stat'><div class='label'>{label}</div><div class='value {cls}'>{value}</div><div class='note'>{note}</div></div>"
                for label, value, cls, note in stats
            ) + "</div><div class='stage-strip'>" + "".join(
                f"<div class='stage'><div class='name'>{name} <span>{ma}</span></div><div class='count'>{stage_counts.get(key, 0)}</div></div>"
                for name, ma, key in stages
            ) + "</div>",
            unsafe_allow_html=True,
        )
    with calendar_col:
        st.markdown("<div class='tj-label'>스캔 날짜 · 숫자는 그날 신호 수</div>", unsafe_allow_html=True)
        render_calendar_component(current_month, selected_date, available_dates, month_options, counts)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("<div class='tj-label'>필터</div>", unsafe_allow_html=True)
    filter_cols = st.columns([1.3, 2.2, 2.5])
    has_puddle = df.get("puddle", pd.Series(dtype=str)).apply(has_text_signal) if not df.empty else pd.Series(dtype=bool)
    with filter_cols[0]:
        type_counts = df["asset_type"].value_counts().to_dict() if "asset_type" in df.columns else {}
        type_filter = chip_filter("종류", ["Stock", "ETF"], "type_filter",
                                  {"Stock": f"주식 {type_counts.get('Stock', 0)}", "ETF": f"ETF {type_counts.get('ETF', 0)}"})
    in_type = df[df["asset_type"] == type_filter] if "asset_type" in df.columns else df
    with filter_cols[1]:
        all_count = int(has_puddle.reindex(in_type.index, fill_value=False).sum()) if len(in_type) else 0
        strong_count = int((in_type.get("signal") == "RSI & Puddle").sum()) if "signal" in in_type.columns else 0
        signal_filter = chip_filter("신호", ["Puddle", "RSI & Puddle"], "signal_filter",
                                    {"Puddle": f"전체 {all_count}", "RSI & Puddle": f"RSI+Puddle {strong_count}"})

    filtered = in_type.copy()
    if "signal" in filtered.columns:
        if signal_filter == "Puddle":
            filtered = filtered[filtered.get("puddle", pd.Series(dtype=str)).apply(has_text_signal)]
        else:
            filtered = filtered[filtered["signal"] == signal_filter]

    st.markdown("<div class='panel-title'><span class='chev'>›</span><span>신호 목록</span>"
                "<span class='tj-caption' style='margin:0 0 0 6px'>행 선택 시 차트</span></div>", unsafe_allow_html=True)
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
    st.download_button("이 목록 CSV 다운로드", data=filtered.drop(columns=["_stage"], errors="ignore").to_csv(index=False).encode("utf-8"), file_name=selected_row["filename"], mime="text/csv", use_container_width=True)
    st.markdown(ui.footer_html(), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
