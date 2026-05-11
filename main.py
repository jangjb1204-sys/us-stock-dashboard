import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from html import escape
import time

from stock_analyzer import (
    TICKER_CONFIGS,
    fetch_common_market_data,
    process_stock_data,
)

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="US Stock Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 스타일 ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'DM Sans', sans-serif !important;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.055) 0%, rgba(255,255,255,0) 22%),
            linear-gradient(205deg, rgba(10,132,255,0.12) 0%, rgba(10,132,255,0) 34%),
            linear-gradient(180deg, #09090b 0%, #050506 42%, #030304 100%) !important;
        color: #f5f5f7 !important;
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        background:
            linear-gradient(115deg, transparent 0%, rgba(255,255,255,0.09) 17%, transparent 31%),
            linear-gradient(72deg, transparent 56%, rgba(10,132,255,0.08) 70%, transparent 84%);
        opacity: 0.58;
        mix-blend-mode: screen;
    }
    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1360px;
        position: relative;
        z-index: 1;
    }
    .app-hero {
        position: relative;
        overflow: hidden;
        margin: 0.25rem 0 1.25rem;
        padding: 1.05rem 1.15rem;
        border: 1px solid rgba(255,255,255,0.13);
        border-radius: 24px;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.16), rgba(255,255,255,0.045) 46%, rgba(255,255,255,0.02)),
            rgba(12,12,14,0.48);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.22),
            inset 0 -1px 0 rgba(255,255,255,0.06),
            0 24px 80px rgba(0,0,0,0.30);
        backdrop-filter: blur(26px) saturate(1.45);
        -webkit-backdrop-filter: blur(26px) saturate(1.45);
    }
    .app-hero::after {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background: linear-gradient(118deg, rgba(255,255,255,0.20), transparent 32%, transparent 72%, rgba(255,255,255,0.06));
        opacity: 0.52;
    }
    .app-hero h1 {
        position: relative;
        z-index: 1;
        margin: 0;
        font-size: 1.88rem;
        line-height: 1.08;
        font-weight: 750;
        letter-spacing: 0;
    }
    .app-hero p {
        position: relative;
        z-index: 1;
        margin: 0.45rem 0 0;
        color: #8e8e93;
        font-size: 0.88rem;
    }
    .section-label {
        color: #8e8e93;
        font-size: 0.74rem;
        font-weight: 700;
        margin: 1.2rem 0 0.45rem;
    }
    .focus-title {
        min-height: 76px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 0 0 0 0.2rem;
    }
    .focus-title .eyebrow {
        color: #8e8e93;
        font-size: 0.72rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .focus-title .name {
        color: #f5f5f7;
        font-size: 1.72rem;
        line-height: 1.05;
        font-weight: 750;
    }
    .focus-title .ticker {
        display: inline-block;
        margin-left: 0.55rem;
        padding: 0.16rem 0.52rem;
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 11px;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.18), rgba(10,132,255,0.12)),
            rgba(10,132,255,0.10);
        color: #b9dcff;
        font-size: 1.06rem;
        font-family: 'DM Mono', monospace;
        font-weight: 500;
        vertical-align: 0.12rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.20);
    }
    .signal-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 0.7rem 0 1.1rem;
    }
    .signal-card {
        position: relative;
        overflow: hidden;
        min-height: 118px;
        padding: 15px 16px;
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 22px;
        background:
            linear-gradient(145deg, rgba(255,255,255,0.16), rgba(255,255,255,0.045) 48%, rgba(255,255,255,0.025)),
            rgba(12,12,14,0.45);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.20),
            inset 0 -1px 0 rgba(255,255,255,0.06),
            0 20px 64px rgba(0,0,0,0.28);
        backdrop-filter: blur(28px) saturate(1.5);
        -webkit-backdrop-filter: blur(28px) saturate(1.5);
    }
    .signal-card::after {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background:
            linear-gradient(118deg, rgba(255,255,255,0.18), transparent 34%),
            linear-gradient(180deg, color-mix(in srgb, var(--accent) 13%, transparent), transparent 58%);
        opacity: 0.72;
    }
    .signal-title {
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        gap: 8px;
        color: #f5f5f7;
        font-size: 0.88rem;
        font-weight: 700;
        margin-bottom: 11px;
    }
    .signal-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: var(--accent);
        box-shadow: 0 0 18px color-mix(in srgb, var(--accent) 55%, transparent);
    }
    .signal-item {
        position: relative;
        z-index: 1;
        display: flex;
        justify-content: space-between;
        gap: 12px;
        padding: 7px 0;
        border-top: 1px solid rgba(255,255,255,0.08);
        color: #d8d8dc;
        font-size: 0.8rem;
    }
    .signal-item:first-of-type { border-top: none; }
    .signal-date {
        color: #8e8e93;
        white-space: nowrap;
        font-family: 'DM Mono', monospace;
        font-size: 0.74rem;
    }
    .signal-empty {
        position: relative;
        z-index: 1;
        padding-top: 14px;
        color: #8e8e93;
        font-size: 0.8rem;
    }

    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background: #0b0b0d !important;
        border-right: 1px solid rgba(255,255,255,0.08) !important;
    }
    section[data-testid="stSidebar"] * { font-family: 'DM Sans', sans-serif !important; }
    section[data-testid="stSidebar"] h2 {
        color: #f5f5f7 !important;
        font-size: 1rem !important;
        font-weight: 650 !important;
        letter-spacing: 0;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] small {
        color: #8e8e93 !important;
        font-size: 0.82rem !important;
    }

    /* 상단 컨트롤 */
    div[data-testid="stSelectbox"] label,
    div[data-testid="stRadio"] label {
        color: #8e8e93 !important;
        font-size: 0.74rem !important;
        font-weight: 600 !important;
        letter-spacing: 0 !important;
    }
    div[data-baseweb="select"] > div {
        background:
            linear-gradient(135deg, rgba(255,255,255,0.13), rgba(255,255,255,0.035)),
            rgba(14,14,16,0.54) !important;
        border: 1px solid rgba(255,255,255,0.16) !important;
        border-radius: 14px !important;
        min-height: 44px !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.16), 0 14px 38px rgba(0,0,0,0.18) !important;
        backdrop-filter: blur(20px) saturate(1.35);
        -webkit-backdrop-filter: blur(20px) saturate(1.35);
    }
    div[data-baseweb="select"] span {
        color: #f5f5f7 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        background:
            linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.03)),
            rgba(14,14,16,0.50);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 999px;
        min-height: 38px;
        padding: 7px 13px;
        margin: 0;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.15), 0 12px 28px rgba(0,0,0,0.14);
        backdrop-filter: blur(18px) saturate(1.28);
        -webkit-backdrop-filter: blur(18px) saturate(1.28);
        transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
        background:
            linear-gradient(145deg, rgba(255,255,255,0.96), rgba(255,255,255,0.72));
        border-color: rgba(255,255,255,0.72);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.90), 0 18px 42px rgba(255,255,255,0.10);
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover { transform: translateY(-1px); }
    div[data-testid="stRadio"] div[role="radiogroup"] label p {
        color: #f5f5f7 !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
        color: #050506 !important;
    }

    /* 메트릭 카드 */
    div[data-testid="metric-container"] {
        background:
            linear-gradient(145deg, rgba(255,255,255,0.13), rgba(255,255,255,0.035) 54%, rgba(255,255,255,0.02)),
            rgba(12,12,14,0.48);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 20px;
        padding: 16px 18px;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.18),
            inset 0 -1px 0 rgba(255,255,255,0.05),
            0 18px 54px rgba(0,0,0,0.22);
        backdrop-filter: blur(24px) saturate(1.42);
        -webkit-backdrop-filter: blur(24px) saturate(1.42);
        transition: border-color 0.15s ease, background 0.15s ease, transform 0.15s ease;
    }
    div[data-testid="metric-container"]:hover {
        background:
            linear-gradient(145deg, rgba(255,255,255,0.17), rgba(255,255,255,0.045)),
            rgba(18,18,20,0.56);
        border-color: rgba(255,255,255,0.24);
        transform: translateY(-1px);
    }
    div[data-testid="metric-container"] label {
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0 !important;
        color: #8e8e93 !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-family: 'DM Mono', monospace !important;
        font-size: 1.26rem !important;
        font-weight: 500 !important;
        color: #f5f5f7 !important;
        letter-spacing: 0;
    }
    div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-size: 0.74rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em;
    }

    /* 탭 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 18px;
        background: transparent;
        border-radius: 0;
        padding: 0;
        border-bottom: 1px solid rgba(255,255,255,0.10);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 0;
        color: #8e8e93;
        font-weight: 600;
        font-size: 0.82rem;
        letter-spacing: 0;
        padding: 8px 2px 12px;
        border-bottom: 2px solid transparent;
        transition: color 0.15s ease, border-color 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover { color: #f5f5f7; background: transparent; }
    .stTabs [aria-selected="true"] {
        background: transparent !important;
        color: #f5f5f7 !important;
        border-bottom-color: #0a84ff;
        box-shadow: none;
    }

    /* 헤딩 */
    h1 {
        color: #f5f5f7 !important;
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        letter-spacing: 0;
    }
    h2 { color: #f5f5f7 !important; font-weight: 700 !important; letter-spacing: 0; }
    h3 {
        color: #f5f5f7 !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        letter-spacing: 0;
    }
    p, li { color: #9b9ba1; font-size: 0.84rem; }

    /* 버튼 */
    .stButton > button {
        background:
            linear-gradient(145deg, rgba(255,255,255,0.26), rgba(255,255,255,0.04)),
            #0a84ff;
        color: #fff;
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.82rem;
        letter-spacing: 0;
        padding: 9px 16px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.26), 0 18px 46px rgba(10,132,255,0.25);
        transition: background 0.15s ease, transform 0.15s ease;
    }
    .stButton > button p { color: #fff !important; }
    .stButton > button:hover {
        background: #2491ff;
        transform: translateY(-1px);
    }

    /* 다운로드 버튼 */
    .stDownloadButton > button {
        background:
            linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.035)),
            rgba(14,14,16,0.50);
        color: #0a84ff;
        border: 1px solid rgba(10,132,255,0.35);
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.82rem;
        transition: background 0.15s ease, border-color 0.15s ease;
    }
    .stDownloadButton > button p { color: #0a84ff !important; }
    .stDownloadButton > button:hover {
        background: rgba(10,132,255,0.10);
        border-color: #0a84ff;
    }

    /* 스피너 */
    .stSpinner > div { border-top-color: #0a84ff !important; }

    /* expander */
    details {
        border: 1px solid rgba(255,255,255,0.16) !important;
        border-radius: 24px !important;
        background:
            linear-gradient(145deg, rgba(255,255,255,0.13), rgba(255,255,255,0.04) 48%, rgba(255,255,255,0.025)),
            rgba(12,12,14,0.46) !important;
        padding: 4px 6px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.18),
            inset 0 -1px 0 rgba(255,255,255,0.05),
            0 22px 70px rgba(0,0,0,0.28);
        backdrop-filter: blur(28px) saturate(1.45);
        -webkit-backdrop-filter: blur(28px) saturate(1.45);
    }
    details summary {
        color: #f5f5f7 !important;
        font-weight: 600;
        font-size: 0.84rem;
        padding: 10px 4px;
    }

    /* code 배지 */
    code {
        background: rgba(10,132,255,0.14) !important;
        color: #8ec5ff !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.78em !important;
        border-radius: 8px !important;
        padding: 2px 8px !important;
        border: 1px solid rgba(10,132,255,0.28) !important;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 18px;
        overflow: hidden;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.10), 0 18px 58px rgba(0,0,0,0.18);
    }

    /* progress bar */
    .stProgress > div > div { background: #0a84ff !important; border-radius: 4px; }

    /* 구분선 */
    hr { border-color: rgba(255,255,255,0.10) !important; margin: 1.35rem 0 !important; }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
            padding-top: 0.9rem !important;
        }
        h1 {
            font-size: 1.1rem !important;
            line-height: 1.25 !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto;
            flex-wrap: nowrap;
        }
        .stTabs [data-baseweb="tab"] {
            min-width: max-content;
            padding: 6px 12px;
            font-size: 0.76rem;
        }
        div[data-testid="metric-container"] {
            padding: 12px 13px;
        }
        div[data-testid="metric-container"] [data-testid="stMetricValue"] {
            font-size: 1rem !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label {
            flex: 1 1 calc(50% - 8px);
            justify-content: center;
        }
        .app-hero h1 {
            font-size: 1.28rem;
        }
        .signal-grid {
            grid-template-columns: 1fr;
        }
        .focus-title {
            min-height: auto;
            padding-top: 0.55rem;
        }
        .focus-title .name {
            font-size: 1.34rem;
        }
        .focus-title .ticker {
            font-size: 0.92rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ── 상수 ───────────────────────────────────────────────────────────────────────
DELTA_OPTIONS  = {"90일": 90, "180일": 180, "1년": 365, "2년": 730, "전체": 9999}
DATA_PERIOD = "4y"

MA_COLORS = {
    "MA20":  "#2196F3",
    "MA60":  "#FF9800",
    "MA120": "#F44336",
    "MA200": "#9C27B0",
}

# ── 숫자 포맷 헬퍼 ─────────────────────────────────────────────────────────────
def fmt_price(v):
    try: return f"${float(v):.2f}"
    except: return "N/A"

def fmt_pct(v, sign=False):
    try:
        f = float(v)
        return f"{f:+.2f}%" if sign else f"{f:.2f}%"
    except: return "N/A"

def fmt_1f(v):
    try: return f"{float(v):.1f}"
    except: return "N/A"

def fmt_int(v):
    try: return f"{int(float(v)):,}"
    except: return "N/A"

def safe_float(val):
    try: return float(val)
    except: return None

def has_rsi_puddle_signal(rsi, puddle) -> bool:
    try:
        rsi_val = float(rsi)
        puddle_text = str(puddle) if pd.notna(puddle) else ''
        return rsi_val <= 30 and any(ch.isalpha() for ch in puddle_text)
    except Exception:
        return False

# ── 캐싱 ───────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def load_common_data(period: str) -> dict:
    return fetch_common_market_data(period=period)

@st.cache_data(ttl=1800, show_spinner=False)
def load_ticker_data(ticker: str, name: str, period: str, delta: int, _cache_key: str) -> pd.DataFrame:
    common = load_common_data(period)
    return process_stock_data(ticker, name, common, period=period, delta=delta)

# ── 차트 공통 테마 ─────────────────────────────────────────────────────────────
CHART_THEME = dict(
    plot_bgcolor='#050506',
    paper_bgcolor='#050506',
    font=dict(family='DM Sans, sans-serif', color='#8e8e93', size=12),
    legend=dict(
        orientation='h', yanchor='bottom', y=1.04, xanchor='right', x=1,
        font=dict(size=11), bgcolor='rgba(0,0,0,0)', bordercolor='rgba(255,255,255,0.10)',
    ),
    xaxis_rangeslider_visible=False,
    margin=dict(l=60, r=24, t=78, b=40),
)
GRID = dict(showgrid=True, gridcolor='rgba(255,255,255,0.07)', zeroline=False)

# ── 캔들스틱 차트 ─────────────────────────────────────────────────────────────
def build_candlestick_chart(df: pd.DataFrame, name: str) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.60, 0.20, 0.20],
        vertical_spacing=0.025,
    )

    fig.add_trace(go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name='Price',
        increasing_line_color='#3fb950', increasing_fillcolor='#3fb950',
        decreasing_line_color='#f85149', decreasing_fillcolor='#f85149',
        whiskerwidth=0.4,
    ), row=1, col=1)

    for ma, color in MA_COLORS.items():
        if ma in df.columns and df[ma].notna().any():
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df[ma], name=ma,
                line=dict(color=color, width=1.4), mode='lines',
            ), row=1, col=1)

    if 'Puddle' in df.columns:
        puddle_df = df[df['Puddle'].str.contains(r'[a-zA-Z]', na=False)]
        if not puddle_df.empty:
            fig.add_trace(go.Scatter(
                x=puddle_df['Date'], y=puddle_df['Low'] * 0.982,
                mode='markers', name='Puddle',
                marker=dict(symbol='triangle-up', size=10, color='#ff7b72',
                            line=dict(width=1, color='white')),
            ), row=1, col=1)

    if 'VIX1D>VIX' in df.columns:
        for d in df[df['VIX1D>VIX'] == 'BUY']['Date']:
            fig.add_vline(x=d, line=dict(color='rgba(255,123,114,0.25)', width=1), row=1, col=1)

    if 'RSI' in df.columns and df['RSI'].notna().any():
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['RSI'], name='RSI',
            line=dict(color='#d2a679', width=1.5),
        ), row=2, col=1)
        fig.add_hline(y=70, line=dict(color='#f85149', width=1, dash='dot'), row=2, col=1)
        fig.add_hline(y=30, line=dict(color='#3fb950', width=1, dash='dot'), row=2, col=1)
        fig.update_yaxes(
            title_text='RSI', range=[0, 100], row=2, col=1,
            tickfont=dict(color='#8e8e93', size=10),
            title=dict(font=dict(color='#8e8e93', size=11)),
        )

    if 'VIX' in df.columns and df['VIX'].notna().any():
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['VIX'], name='VIX',
            line=dict(color='#79c0ff', width=1.5),
            fill='tozeroy', fillcolor='rgba(121,192,255,0.07)',
        ), row=3, col=1)
        fig.add_hline(y=25, line=dict(color='#3fb950', width=1, dash='dot'), row=3, col=1)
        fig.update_yaxes(
            title_text='VIX', row=3, col=1,
            tickfont=dict(color='#8e8e93', size=10),
            title=dict(font=dict(color='#8e8e93', size=11)),
        )

    fig.update_layout(
        **CHART_THEME,
        title=dict(text=f'<b>{name}</b>  캔들스틱', x=0.01,
                   font=dict(size=15, color='#f5f5f7', family='DM Sans')),
        height=660,
    )
    for r in [1, 2, 3]:
        fig.update_xaxes(**GRID, row=r, col=1, tickfont=dict(color='#8e8e93', size=10))
        fig.update_yaxes(**GRID, row=r, col=1)

    return fig

# ── 라인 차트 ─────────────────────────────────────────────────────────────────
def build_line_chart(df: pd.DataFrame, name: str) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.68, 0.32], vertical_spacing=0.03,
    )

    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Close'], name=f'{name} Close',
        line=dict(color='#f5f5f7', width=2),
    ), row=1, col=1)

    for ma, color in MA_COLORS.items():
        if ma in df.columns and df[ma].notna().any():
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df[ma], name=ma,
                line=dict(color=color, width=1.2, dash='dot'),
            ), row=1, col=1)

    if 'VIX1D>VIX' in df.columns:
        for d in df[df['VIX1D>VIX'] == 'BUY']['Date']:
            fig.add_vline(x=d, line=dict(color='rgba(248,81,73,0.3)', width=1), row=1, col=1)

    if 'RSI' in df.columns and 'Puddle' in df.columns:
        oversold  = df[df['RSI'] <= 30]
        puddle_df = df[df['Puddle'].str.contains(r'[a-zA-Z]', na=False)]
        overlap   = pd.merge(oversold, puddle_df, on='Date', how='inner')
        if not overlap.empty:
            fig.add_trace(go.Scatter(
                x=overlap['Date'], y=overlap['Close_x'],
                mode='markers', name='RSI ∩ Puddle',
                marker=dict(symbol='circle', size=9, color='#bc8cff',
                            line=dict(width=1.5, color='white')),
            ), row=1, col=1)

    if 'FG index' in df.columns and df['FG index'].notna().any():
        fg_df = df[df['FG index'].notna()]
        fg_zones = [
            (0, 25,  '극도 공포', 'rgba(248,81,73,0.14)'),
            (25, 45, '공포',     'rgba(210,153,34,0.12)'),
            (45, 55, '중립',     'rgba(88,166,255,0.10)'),
            (55, 75, '탐욕',     'rgba(63,185,80,0.11)'),
            (75, 100, '극도 탐욕', 'rgba(63,185,80,0.18)'),
        ]
        for y0, y1, label, color in fg_zones:
            fig.add_hrect(
                y0=y0, y1=y1,
                fillcolor=color, line_width=0,
                annotation_text=label, annotation_position='left',
                annotation_font=dict(size=10, color='#8e8e93'),
                row=2, col=1,
            )
        fig.add_trace(go.Scatter(
            x=fg_df['Date'], y=fg_df['FG index'], name='Fear & Greed',
            mode='lines',
            line=dict(color='#f5f5f7', width=2.4, shape='spline'),
            hovertemplate='%{x|%Y-%m-%d}<br>F&G %{y:.0f}<extra></extra>',
        ), row=2, col=1)
        latest_fg = fg_df.iloc[-1]
        fig.add_trace(go.Scatter(
            x=[latest_fg['Date']], y=[latest_fg['FG index']], name='현재 F&G',
            mode='markers+text',
            marker=dict(size=13, color='#0a84ff', line=dict(width=2, color='#f5f5f7')),
            text=[f"{latest_fg['FG index']:.0f}"],
            textposition='middle right',
            textfont=dict(size=12, color='#f5f5f7'),
            hovertemplate='%{x|%Y-%m-%d}<br>현재 F&G %{y:.0f}<extra></extra>',
        ), row=2, col=1)
        for level in [25, 45, 55, 75]:
            fig.add_hline(y=level, line=dict(color='rgba(138,168,192,0.24)', width=1, dash='dot'), row=2, col=1)
        fig.add_hline(y=50, line=dict(color='#0a84ff', width=1.4, dash='solid'), row=2, col=1)
        fig.update_yaxes(
            title_text='F&G', range=[0, 100], row=2, col=1,
            tickfont=dict(color='#8e8e93', size=10),
            title=dict(font=dict(color='#8e8e93', size=11)),
        )

    fig.update_layout(
        **CHART_THEME,
        title=dict(text=f'<b>{name}</b>  라인 + 신호', x=0.01,
                   font=dict(size=15, color='#f5f5f7', family='DM Sans')),
        height=590,
    )
    for r in [1, 2]:
        fig.update_xaxes(**GRID, row=r, col=1, tickfont=dict(color='#8e8e93', size=10))
        fig.update_yaxes(**GRID, row=r, col=1)

    return fig

# ── 테이블 스타일 ───────────────────────────────────────────────────────────────
def style_table(df: pd.DataFrame):
    display_cols = [
        'Date', 'Close', 'Change(%)', '2sigma(%)',
        'RSI', 'FG index', 'FG/RSI signal', 'SS Signal',
        'Puddle', 'VIX', 'VIX1D', 'VIX1D>VIX', 'SKEW', '10Y Treasury',
    ]
    existing = [c for c in display_cols if c in df.columns]
    sub = df[existing].iloc[::-1].copy()

    # 화면 표시용 숫자 정리
    if 'Date' in sub.columns:
        sub['Date'] = pd.to_datetime(sub['Date']).dt.strftime('%Y-%m-%d')
    numeric_cols = [
        'Close', 'Change(%)', '2sigma(%)', 'RSI', 'FG index',
        'VIX', 'VIX1D', 'SKEW', '10Y Treasury',
    ]
    for col in numeric_cols:
        if col in sub.columns:
            sub[col] = pd.to_numeric(sub[col], errors='coerce')

    def color_row(row):
        styles = [''] * len(row)
        idx = list(row.index)
        def si(col): return idx.index(col) if col in idx else -1

        ci  = si('Change(%)')
        sci = si('2sigma(%)')
        ri  = si('RSI')
        pi  = si('Puddle')

        def bg_prefix(style):
            return f"{style}; " if style.startswith('background') else ''

        # 라인 차트의 RSI ∩ Puddle 동그라미와 같은 조건
        if ri >= 0 and pi >= 0:
            try:
                if has_rsi_puddle_signal(row.iloc[ri], row.iloc[pi]):
                    styles = ['background-color: rgba(188,140,255,0.20)'] * len(styles)
            except: pass

        # 2sigma 배경
        if ci >= 0 and sci >= 0:
            try:
                chg = float(row.iloc[ci]) if pd.notna(row.iloc[ci]) else 0
                sig = float(row.iloc[sci]) if pd.notna(row.iloc[sci]) else 0
                if chg < -sig and not styles[ci].startswith('background'):
                    styles = ['background-color: rgba(210,153,34,0.18)'] * len(styles)
            except: pass

        # Change(%) 글자색
        if ci >= 0 and pd.notna(row.iloc[ci]) and row.iloc[ci] != '':
            try:
                v = float(row.iloc[ci])
                bg = bg_prefix(styles[ci])
                styles[ci] = f'{bg}color: #f85149; font-weight:600' if v < 0 else \
                             f'{bg}color: #3fb950; font-weight:600' if v > 0 else styles[ci]
            except: pass

        # RSI
        if ri >= 0 and pd.notna(row.iloc[ri]) and row.iloc[ri] != '':
            try:
                v = float(row.iloc[ri])
                bg = bg_prefix(styles[ri])
                styles[ri] = f'{bg}color: #3fb950; font-weight:600' if v <= 30 else \
                             f'{bg}color: #f85149; font-weight:600' if v >= 70 else styles[ri]
            except: pass

        # VIX
        vi = si('VIX')
        if vi >= 0 and pd.notna(row.iloc[vi]) and row.iloc[vi] != '':
            try:
                if float(row.iloc[vi]) > 25:
                    styles[vi] = f'{bg_prefix(styles[vi])}color: #3fb950; font-weight:600'
            except: pass

        # SKEW
        ski = si('SKEW')
        if ski >= 0 and pd.notna(row.iloc[ski]) and row.iloc[ski] != '':
            try:
                v = float(row.iloc[ski])
                bg = bg_prefix(styles[ski])
                styles[ski] = f'{bg}color: #f85149; font-weight:600' if v >= 155 else \
                              f'{bg}color: #3fb950; font-weight:600' if v <= 127 else styles[ski]
            except: pass

        return styles

    formatters = {
        'Close':        lambda x: f"${x:,.2f}",
        'Change(%)':   lambda x: f"{x:+.2f}%",
        '2sigma(%)':   lambda x: f"{x:.1f}%",
        'RSI':         lambda x: f"{x:.1f}",
        'FG index':    lambda x: f"{int(round(x))}",
        'VIX':         lambda x: f"{x:.1f}",
        'VIX1D':       lambda x: f"{x:.1f}",
        'SKEW':        lambda x: f"{x:.1f}",
        '10Y Treasury': lambda x: f"{x:.2f}%",
    }
    existing_formatters = {
        col: formatter for col, formatter in formatters.items()
        if col in sub.columns
    }

    return (
        sub.style
        .apply(color_row, axis=1)
        .format(existing_formatters, na_rep='—')
    )


# ── 전체 종목 요약 ─────────────────────────────────────────────────────────────
def render_market_summary(period: str, delta: int, cache_key: str):
    with st.expander("전체 종목 최신 현황", expanded=True):
        summary_rows = []
        prog  = st.progress(0, text="전체 종목 데이터 로딩 중...")
        total = len(TICKER_CONFIGS)

        for i, (ticker, name) in enumerate(TICKER_CONFIGS.items()):
            try:
                d = load_ticker_data(ticker, name, period, delta, cache_key)
                if not d.empty:
                    lat = d.iloc[-1]
                    summary_rows.append({
                        '종목':          name,
                        '종가':          safe_float(lat.get('Close')),
                        'Change(%)':     safe_float(lat.get('Change(%)')),
                        '2sigma(%)':     safe_float(lat.get('2sigma(%)')),
                        'RSI':           safe_float(lat.get('RSI')),
                        'FG/RSI signal': lat.get('FG/RSI signal', ''),
                        'Puddle':        lat.get('Puddle', ''),
                    })
            except Exception:
                pass
            prog.progress((i + 1) / total, text=f"로딩 중... {name}")
            time.sleep(0.05)
        prog.empty()

        if summary_rows:
            summary_df = pd.DataFrame(summary_rows)

            def hl_change(val):
                try:
                    v = float(val)
                    return 'color: #f85149; font-weight:600' if v < 0 else \
                           'color: #3fb950; font-weight:600' if v > 0 else ''
                except: return ''

            def hl_rsi(val):
                try:
                    v = float(val)
                    return 'color: #3fb950; font-weight:600' if v <= 30 else \
                           'color: #f85149; font-weight:600' if v >= 70 else ''
                except: return ''

            def hl_signal_row(row):
                if has_rsi_puddle_signal(row.get('RSI'), row.get('Puddle')):
                    return ['background-color: rgba(188,140,255,0.20)'] * len(row)
                return [''] * len(row)

            styled_summary = (
                summary_df.style
                .apply(hl_signal_row, axis=1)
                .map(hl_change, subset=['Change(%)'])
                .map(hl_rsi,    subset=['RSI'])
                .format({
                    '종가':      lambda x: f"${x:.2f}" if pd.notna(x) else '—',
                    'Change(%)': lambda x: f"{x:+.2f}%" if pd.notna(x) else '—',
                    '2sigma(%)': lambda x: f"{x:.1f}%" if pd.notna(x) else '—',
                    'RSI':       lambda x: f"{x:.1f}"  if pd.notna(x) else '—',
                    'Puddle':    lambda x: x if isinstance(x, str) and x else '—',
                })
            )
            st.dataframe(styled_summary, use_container_width=True, hide_index=True)
        else:
            st.info("전체 종목 데이터를 아직 가져오지 못했습니다.")


def render_signal_cards(df: pd.DataFrame):
    def make_items(rows, value_col=None):
        items = []
        for _, row in rows.iterrows():
            date = pd.to_datetime(row['Date']).strftime('%m.%d')
            value = row.get(value_col, '') if value_col else ''
            items.append((date, str(value) if pd.notna(value) and value else 'Signal'))
        return items

    puddle_items = make_items(
        df[df['Puddle'].str.contains(r'[a-zA-Z]', na=False)].tail(3),
        'Puddle',
    ) if 'Puddle' in df.columns else []

    vix_items = make_items(
        df[df['VIX1D>VIX'] == 'BUY'].tail(3),
    ) if 'VIX1D>VIX' in df.columns else []

    stochastic_items = make_items(
        df[df['SS Signal'].isin(['Buy', 'Sell'])].tail(3),
        'SS Signal',
    ) if 'SS Signal' in df.columns else []

    cards = [
        ('Puddle', puddle_items, '#bf5af2'),
        ('VIX1D > VIX', vix_items, '#0a84ff'),
        ('Stochastic', stochastic_items, '#30d158'),
    ]
    html_cards = []
    for title, items, accent in cards:
        body = ''.join(
            f"<div class='signal-item'><span class='signal-date'>{escape(date)}</span>"
            f"<span>{escape(value)}</span></div>"
            for date, value in items
        )
        if not body:
            body = "<div class='signal-empty'>최근 신호 없음</div>"
        html_cards.append(
            f"<div class='signal-card' style='--accent:{accent}'>"
            f"<div class='signal-title'><span class='signal-dot'></span>{escape(title)}</div>"
            f"{body}</div>"
        )

    st.markdown(f"<div class='signal-grid'>{''.join(html_cards)}</div>", unsafe_allow_html=True)


def render_rsi_puddle_dates(df: pd.DataFrame, limit: int = 5):
    if not {'Date', 'RSI', 'Puddle'}.issubset(df.columns):
        st.info("RSI & Puddle 신호 데이터가 아직 없습니다.")
        return

    signal_df = df[df.apply(lambda row: has_rsi_puddle_signal(row.get('RSI'), row.get('Puddle')), axis=1)].tail(limit)
    if signal_df.empty:
        st.info("선택한 표시 범위 안에는 RSI & Puddle 중복 신호가 없습니다.")
        return

    items = []
    for _, row in signal_df.iloc[::-1].iterrows():
        date = pd.to_datetime(row['Date']).strftime('%Y-%m-%d')
        rsi = safe_float(row.get('RSI'))
        rsi_text = f"RSI {rsi:.1f}" if rsi is not None else "RSI —"
        puddle = str(row.get('Puddle', '')) if pd.notna(row.get('Puddle')) else ''
        items.append(
            f"<div class='signal-item'><span class='signal-date'>{escape(date)}</span>"
            f"<span>{escape(rsi_text)} · {escape(puddle)}</span></div>"
        )

    st.markdown(
        "<div class='signal-card' style='--accent:#bf5af2'>"
        "<div class='signal-title'><span class='signal-dot'></span>RSI & Puddle 중복 신호</div>"
        f"{''.join(items)}</div>",
        unsafe_allow_html=True,
    )


# ── 상단 컨트롤 ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## US Stock Dashboard")
    st.caption(f"마지막 업데이트\n{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption("캐시 유효시간: 30분")
    if st.button("데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

ticker_options = list(TICKER_CONFIGS.keys())

st.markdown(
    """
    <div class="app-hero">
      <h1>US Stock Dashboard</h1>
      <p>시장 전체를 먼저 훑고, 관심 종목을 깊게 확인합니다.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
ctrl_delta, ctrl_action = st.columns([3.2, 0.8])

with ctrl_delta:
    delta_label = st.radio(
        "표시 범위",
        options=list(DELTA_OPTIONS.keys()),
        index=list(DELTA_OPTIONS.keys()).index("180일"),
        horizontal=True,
    )
    delta = DELTA_OPTIONS[delta_label]

with ctrl_action:
    st.markdown("<div style='height: 1.7rem'></div>", unsafe_allow_html=True)
    if st.button("새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ── 메인 영역 ──────────────────────────────────────────────────────────────────
period = DATA_PERIOD
cache_key = f"{period}_{delta}"

render_market_summary(period, delta, cache_key)
st.markdown("---")

st.markdown("<div class='section-label'>포커스 종목</div>", unsafe_allow_html=True)
focus_selector, focus_title = st.columns([1.15, 2.85])
with focus_selector:
    selected_ticker = st.selectbox(
        "종목",
        ticker_options,
        format_func=lambda ticker: f"{TICKER_CONFIGS[ticker]} · {ticker}",
        label_visibility="collapsed",
    )
    selected_name = TICKER_CONFIGS[selected_ticker]

with focus_title:
    st.markdown(
        f"""
        <div class="focus-title">
          <div class="eyebrow">Selected</div>
          <div class="name">{escape(selected_name)} <span class="ticker">{escape(selected_ticker)}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.spinner(f"{selected_name} 데이터 불러오는 중..."):
    df = load_ticker_data(selected_ticker, selected_name, period, delta, cache_key)

if df.empty:
    st.error(f"{selected_ticker} 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

table_df = load_ticker_data(
    selected_ticker,
    selected_name,
    period,
    DELTA_OPTIONS["전체"],
    f"{period}_{DELTA_OPTIONS['전체']}",
)
if table_df.empty:
    table_df = df

latest = df.iloc[-1]

# ── 메트릭 카드 ────────────────────────────────────────────────────────────────
close_val    = safe_float(latest.get('Close'))
change_val   = safe_float(latest.get('Change(%)'))
rsi_val      = safe_float(latest.get('RSI'))
vix_val      = safe_float(latest.get('VIX'))
fg_val       = safe_float(latest.get('FG index'))
skew_val     = safe_float(latest.get('SKEW'))
treasury_val = safe_float(latest.get('10Y Treasury'))

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("종가", fmt_price(close_val),
              fmt_pct(change_val, sign=True) if change_val is not None else None)

with col2:
    rsi_label = ("과매도" if rsi_val and rsi_val <= 30 else
                 "과매수" if rsi_val and rsi_val >= 70 else
                 "중립"   if rsi_val else "")
    st.metric("RSI", fmt_1f(rsi_val) if rsi_val else "N/A", rsi_label)

with col3:
    vix_label = "급등구간" if vix_val and vix_val > 25 else ""
    st.metric("VIX", fmt_1f(vix_val) if vix_val else "N/A", vix_label)

col4, col5, col6 = st.columns(3)

with col4:
    fg_label = ""
    if fg_val is not None:
        fg_label = ("극도 탐욕" if fg_val >= 75 else "탐욕"    if fg_val >= 55
               else "중립"     if fg_val >= 45 else "공포"    if fg_val >= 25
               else "극도 공포")
    st.metric("F&G", fmt_int(fg_val) if fg_val is not None else "N/A", fg_label)

with col5:
    skew_label = ("고위험" if skew_val and skew_val >= 155 else
                  "저위험" if skew_val and skew_val <= 127 else "")
    st.metric("SKEW", fmt_1f(skew_val) if skew_val else "N/A", skew_label)

with col6:
    st.metric("10Y Treasury",
              f"{treasury_val:.2f}%" if treasury_val else "N/A")

st.markdown("")

# ── 탭 ────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["캔들스틱", "라인 + 신호", "데이터"])

with tab1:
    st.plotly_chart(build_candlestick_chart(df, selected_name), use_container_width=True)

    st.markdown("### 최근 신호")
    render_signal_cards(df)

with tab2:
    st.plotly_chart(build_line_chart(df, selected_name), use_container_width=True)

    st.markdown("### RSI & Puddle 최근 신호")
    render_rsi_puddle_dates(df)

with tab3:
    st.markdown("### 전체 데이터")
    st.dataframe(style_table(table_df), use_container_width=True, height=500)

    csv = table_df.copy()
    if 'Date' in csv.columns:
        csv['Date'] = pd.to_datetime(csv['Date']).dt.strftime('%Y-%m-%d')
    st.download_button(
        label="CSV 다운로드",
        data=csv.to_csv(index=False, encoding='utf-8-sig'),
        file_name=f"{selected_name}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
