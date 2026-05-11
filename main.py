import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
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
        background-color: #0b0f19 !important;
    }
    .block-container {
        padding-top: 1.4rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1440px;
    }

    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background: #0e1420 !important;
        border-right: 1px solid #1c2840 !important;
    }
    section[data-testid="stSidebar"] * { font-family: 'DM Sans', sans-serif !important; }
    section[data-testid="stSidebar"] h2 {
        color: #e2e8f0 !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] small {
        color: #6b7f96 !important;
        font-size: 0.82rem !important;
    }

    /* 상단 컨트롤 */
    div[data-testid="stSelectbox"] label,
    div[data-testid="stRadio"] label {
        color: #8aa8c0 !important;
        font-size: 0.76rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase;
    }
    div[data-baseweb="select"] > div {
        background: #0e1420 !important;
        border: 1px solid #1c2d42 !important;
        border-radius: 8px !important;
        min-height: 42px !important;
    }
    div[data-baseweb="select"] span {
        color: #dde6f0 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        background: #0e1420;
        border: 1px solid #1c2d42;
        border-radius: 8px;
        min-height: 42px;
        padding: 7px 9px;
        margin: 0;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
        background: #163322;
        border-color: #238636;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label p {
        color: #dde6f0 !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
    }

    /* 메트릭 카드 */
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #111827 0%, #0d1520 100%);
        border: 1px solid #1c2d42;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.4);
        transition: border-color 0.2s ease;
    }
    div[data-testid="metric-container"]:hover { border-color: #2d5a8e; }
    div[data-testid="metric-container"] label {
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase;
        color: #4a6880 !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-family: 'DM Mono', monospace !important;
        font-size: 1.3rem !important;
        font-weight: 500 !important;
        color: #dde6f0 !important;
        letter-spacing: -0.01em;
    }
    div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em;
    }

    /* 탭 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #0e1420;
        border-radius: 10px;
        padding: 5px;
        border: 1px solid #1c2840;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 7px;
        color: #6b7f96;
        font-weight: 600;
        font-size: 0.87rem;
        letter-spacing: 0.02em;
        padding: 6px 20px;
        transition: all 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover { color: #c0d0e0; background: #162030; }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1a6b3c, #1f8040) !important;
        color: #fff !important;
        box-shadow: 0 2px 8px rgba(30,120,60,0.4);
    }

    /* 헤딩 */
    h1 {
        color: #e2e8f0 !important;
        font-size: 1.65rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }
    h2 { color: #c4d4e4 !important; font-weight: 700 !important; }
    h3 {
        color: #8aa8c0 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    p, li { color: #6b7f96; font-size: 0.88rem; }

    /* 버튼 */
    .stButton > button {
        background: linear-gradient(135deg, #1a6b3c, #208040);
        color: #fff;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.03em;
        padding: 8px 16px;
        box-shadow: 0 2px 8px rgba(30,120,60,0.3);
        transition: all 0.2s ease;
    }
    .stButton > button p { color: #fff !important; }
    .stButton > button:hover {
        background: linear-gradient(135deg, #20844a, #26a050);
        box-shadow: 0 4px 14px rgba(30,120,60,0.45);
        transform: translateY(-1px);
    }

    /* 다운로드 버튼 */
    .stDownloadButton > button {
        background: #0e1420;
        color: #58a6ff;
        border: 1px solid #1c3a5e;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        transition: all 0.15s ease;
    }
    .stDownloadButton > button:hover {
        background: #162030;
        border-color: #58a6ff;
    }

    /* 스피너 */
    .stSpinner > div { border-top-color: #238636 !important; }

    /* expander */
    details {
        border: 1px solid #1c2840 !important;
        border-radius: 10px !important;
        background: #0e1420 !important;
        padding: 4px !important;
    }
    details summary {
        color: #8aa8c0 !important;
        font-weight: 600;
        font-size: 0.9rem;
        padding: 8px 4px;
    }

    /* code 배지 */
    code {
        background: #162030 !important;
        color: #79c0ff !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.83em !important;
        border-radius: 5px !important;
        padding: 2px 8px !important;
        border: 1px solid #1c3a5e !important;
    }

    /* progress bar */
    .stProgress > div > div { background: #238636 !important; border-radius: 4px; }

    /* 구분선 */
    hr { border-color: #1c2840 !important; margin: 1.2rem 0 !important; }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
            padding-top: 0.9rem !important;
        }
        h1 {
            font-size: 1.22rem !important;
            line-height: 1.25 !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto;
            flex-wrap: nowrap;
        }
        .stTabs [data-baseweb="tab"] {
            min-width: max-content;
            padding: 6px 12px;
            font-size: 0.8rem;
        }
        div[data-testid="metric-container"] {
            padding: 11px 12px;
        }
        div[data-testid="metric-container"] [data-testid="stMetricValue"] {
            font-size: 1.05rem !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label {
            flex: 1 1 calc(50% - 8px);
            justify-content: center;
        }
    }
</style>
""", unsafe_allow_html=True)

# ── 상수 ───────────────────────────────────────────────────────────────────────
PERIOD_OPTIONS = {"6개월": "6mo", "1년": "1y", "2년": "2y", "4년": "4y"}
DELTA_OPTIONS  = {"90일": 90, "180일": 180, "1년": 365, "2년": 730, "전체": 9999}

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
    plot_bgcolor='#080d16',
    paper_bgcolor='#080d16',
    font=dict(family='DM Sans, sans-serif', color='#6b7f96', size=12),
    legend=dict(
        orientation='h', yanchor='bottom', y=1.01, xanchor='left', x=0,
        font=dict(size=11), bgcolor='rgba(0,0,0,0)', bordercolor='#1c2840',
    ),
    xaxis_rangeslider_visible=False,
    margin=dict(l=60, r=20, t=65, b=40),
)
GRID = dict(showgrid=True, gridcolor='#111c2c', zeroline=False)

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
            tickfont=dict(color='#6b7f96', size=10),
            title=dict(font=dict(color='#6b7f96', size=11)),
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
            tickfont=dict(color='#6b7f96', size=10),
            title=dict(font=dict(color='#6b7f96', size=11)),
        )

    fig.update_layout(
        **CHART_THEME,
        title=dict(text=f'<b>{name}</b>  캔들스틱', x=0.01,
                   font=dict(size=17, color='#dde6f0', family='DM Sans')),
        height=660,
    )
    for r in [1, 2, 3]:
        fig.update_xaxes(**GRID, row=r, col=1, tickfont=dict(color='#6b7f96', size=10))
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
        line=dict(color='#dde6f0', width=2),
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
        fig.add_trace(go.Bar(
            x=fg_df['Date'], y=fg_df['FG index'], name='Fear & Greed',
            marker=dict(
                color=fg_df['FG index'],
                colorscale=[[0, '#f85149'], [0.5, '#d29922'], [1, '#3fb950']],
                cmin=0, cmax=100,
            ),
        ), row=2, col=1)
        fig.add_hline(y=50, line=dict(color='#58a6ff', width=1, dash='dot'), row=2, col=1)
        fig.update_yaxes(
            title_text='F&G', range=[0, 100], row=2, col=1,
            tickfont=dict(color='#6b7f96', size=10),
            title=dict(font=dict(color='#6b7f96', size=11)),
        )

    fig.update_layout(
        **CHART_THEME,
        title=dict(text=f'<b>{name}</b>  라인 + 신호', x=0.01,
                   font=dict(size=17, color='#dde6f0', family='DM Sans')),
        height=590,
    )
    for r in [1, 2]:
        fig.update_xaxes(**GRID, row=r, col=1, tickfont=dict(color='#6b7f96', size=10))
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
    sub = df[existing].tail(30).iloc[::-1].copy()

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

        # 2sigma 배경 (먼저 적용)
        if ci >= 0 and sci >= 0:
            try:
                chg = float(row.iloc[ci]) if pd.notna(row.iloc[ci]) else 0
                sig = float(row.iloc[sci]) if pd.notna(row.iloc[sci]) else 0
                if chg < -sig:
                    styles = ['background-color: rgba(210,153,34,0.18)'] * len(styles)
            except: pass

        # Change(%) 글자색
        if ci >= 0 and pd.notna(row.iloc[ci]) and row.iloc[ci] != '':
            try:
                v = float(row.iloc[ci])
                bg = 'background-color: rgba(210,153,34,0.18); ' if styles[ci].startswith('background') else ''
                styles[ci] = f'{bg}color: #f85149; font-weight:600' if v < 0 else \
                             f'{bg}color: #3fb950; font-weight:600' if v > 0 else styles[ci]
            except: pass

        # RSI
        ri = si('RSI')
        if ri >= 0 and pd.notna(row.iloc[ri]) and row.iloc[ri] != '':
            try:
                v = float(row.iloc[ri])
                styles[ri] = 'color: #3fb950; font-weight:600' if v <= 30 else \
                             'color: #f85149; font-weight:600' if v >= 70 else ''
            except: pass

        # VIX
        vi = si('VIX')
        if vi >= 0 and pd.notna(row.iloc[vi]) and row.iloc[vi] != '':
            try:
                if float(row.iloc[vi]) > 25: styles[vi] = 'color: #3fb950; font-weight:600'
            except: pass

        # SKEW
        ski = si('SKEW')
        if ski >= 0 and pd.notna(row.iloc[ski]) and row.iloc[ski] != '':
            try:
                v = float(row.iloc[ski])
                styles[ski] = 'color: #f85149; font-weight:600' if v >= 155 else \
                              'color: #3fb950; font-weight:600' if v <= 127 else ''
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


# ── 상단 컨트롤 ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 US Stock Dashboard")
    st.caption(f"⏱ 마지막 업데이트\n{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption("캐시 유효시간: 30분")
    if st.button("🔄  데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

ticker_options = list(TICKER_CONFIGS.keys())

st.markdown("# 📈 US Stock Dashboard")
ctrl_ticker, ctrl_action = st.columns([3.2, 0.8])

with ctrl_ticker:
    selected_ticker = st.selectbox(
        "종목",
        ticker_options,
        format_func=lambda ticker: f"{TICKER_CONFIGS[ticker]} · {ticker}",
        label_visibility="visible",
    )
    selected_name = TICKER_CONFIGS[selected_ticker]

with ctrl_action:
    st.markdown("<div style='height: 1.7rem'></div>", unsafe_allow_html=True)
    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

ctrl_period, ctrl_delta = st.columns([1, 1])

with ctrl_period:
    period_label = st.radio(
        "데이터 기간",
        options=list(PERIOD_OPTIONS.keys()),
        index=list(PERIOD_OPTIONS.keys()).index("2년"),
        horizontal=True,
    )
    period = PERIOD_OPTIONS[period_label]

with ctrl_delta:
    delta_label = st.radio(
        "표시 범위",
        options=list(DELTA_OPTIONS.keys()),
        index=list(DELTA_OPTIONS.keys()).index("180일"),
        horizontal=True,
    )
    delta = DELTA_OPTIONS[delta_label]


# ── 메인 영역 ──────────────────────────────────────────────────────────────────
st.markdown(f"## {selected_name} &nbsp; `{selected_ticker}`", unsafe_allow_html=True)

cache_key = f"{period}_{delta}"
with st.spinner(f"{selected_name} 데이터 불러오는 중..."):
    df = load_ticker_data(selected_ticker, selected_name, period, delta, cache_key)

if df.empty:
    st.error(f"❌ {selected_ticker} 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

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
    st.metric("💰 종가", fmt_price(close_val),
              fmt_pct(change_val, sign=True) if change_val is not None else None)

with col2:
    rsi_label = ("🟢 과매도" if rsi_val and rsi_val <= 30 else
                 "🔴 과매수" if rsi_val and rsi_val >= 70 else
                 "⚪ 중립"   if rsi_val else "")
    st.metric("📊 RSI", fmt_1f(rsi_val) if rsi_val else "N/A", rsi_label)

with col3:
    vix_label = "🟢 급등구간" if vix_val and vix_val > 25 else ""
    st.metric("😨 VIX", fmt_1f(vix_val) if vix_val else "N/A", vix_label)

col4, col5, col6 = st.columns(3)

with col4:
    fg_label = ""
    if fg_val is not None:
        fg_label = ("극도 탐욕" if fg_val >= 75 else "탐욕"    if fg_val >= 55
               else "중립"     if fg_val >= 45 else "공포"    if fg_val >= 25
               else "극도 공포")
    st.metric("🎭 F&G", fmt_int(fg_val) if fg_val is not None else "N/A", fg_label)

with col5:
    skew_label = ("🔴 고위험" if skew_val and skew_val >= 155 else
                  "🟢 저위험" if skew_val and skew_val <= 127 else "")
    st.metric("📐 SKEW", fmt_1f(skew_val) if skew_val else "N/A", skew_label)

with col6:
    st.metric("🏦 10Y Treasury",
              f"{treasury_val:.2f}%" if treasury_val else "N/A")

st.markdown("")

# ── 탭 ────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🕯️  캔들스틱 차트", "📉  라인 + 신호 차트", "📋  데이터 테이블"])

with tab1:
    st.plotly_chart(build_candlestick_chart(df, selected_name), use_container_width=True)

    st.markdown("### 📌 최근 신호 요약")
    sc1, sc2, sc3 = st.columns(3)

    with sc1:
        st.markdown("**🔴 Puddle 신호**")
        if 'Puddle' in df.columns:
            rp = df[df['Puddle'].str.contains(r'[a-zA-Z]', na=False)].tail(3)
            if not rp.empty:
                for _, r in rp.iterrows():
                    st.markdown(f"- {pd.to_datetime(r['Date']).strftime('%Y-%m-%d')} · {r['Puddle']}")
            else:
                st.markdown("최근 없음")

    with sc2:
        st.markdown("**🟢 VIX1D > VIX BUY**")
        if 'VIX1D>VIX' in df.columns:
            rv = df[df['VIX1D>VIX'] == 'BUY'].tail(3)
            if not rv.empty:
                for _, r in rv.iterrows():
                    st.markdown(f"- {pd.to_datetime(r['Date']).strftime('%Y-%m-%d')}")
            else:
                st.markdown("최근 없음")

    with sc3:
        st.markdown("**🔵 Stochastic 신호**")
        if 'SS Signal' in df.columns:
            rs = df[df['SS Signal'].isin(['Buy', 'Sell'])].tail(3)
            if not rs.empty:
                for _, r in rs.iterrows():
                    em = "🟢" if r['SS Signal'] == 'Buy' else "🔴"
                    st.markdown(f"- {pd.to_datetime(r['Date']).strftime('%Y-%m-%d')} · {em} {r['SS Signal']}")
            else:
                st.markdown("최근 없음")

with tab2:
    st.plotly_chart(build_line_chart(df, selected_name), use_container_width=True)

    if 'FG/RSI signal' in df.columns:
        st.markdown("### 📊 FG/RSI 신호 분포")
        sc = df['FG/RSI signal'].value_counts().reset_index()
        sc.columns = ['신호', '횟수']
        st.dataframe(sc, hide_index=True, use_container_width=False)

with tab3:
    st.markdown("### 📋 최근 30일 데이터")
    st.dataframe(style_table(df), use_container_width=True, height=500)

    csv = df.copy()
    if 'Date' in csv.columns:
        csv['Date'] = pd.to_datetime(csv['Date']).dt.strftime('%Y-%m-%d')
    st.download_button(
        label="⬇️  전체 데이터 CSV 다운로드",
        data=csv.to_csv(index=False, encoding='utf-8-sig'),
        file_name=f"{selected_name}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

# ── 전체 종목 요약 ─────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🗂  전체 종목 최신 현황 (클릭해서 펼치기)", expanded=False):
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
                    'Ticker':        ticker,
                    '종가':          safe_float(lat.get('Close')),
                    'Change(%)':     safe_float(lat.get('Change(%)')),
                    'RSI':           safe_float(lat.get('RSI')),
                    'FG/RSI signal': lat.get('FG/RSI signal', ''),
                    'VIX':           safe_float(lat.get('VIX')),
                    'SKEW':          safe_float(lat.get('SKEW')),
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

        styled_summary = (
            summary_df.style
            .map(hl_change, subset=['Change(%)'])
            .map(hl_rsi,    subset=['RSI'])
            .format({
                '종가':      lambda x: f"${x:.2f}" if pd.notna(x) else '—',
                'Change(%)': lambda x: f"{x:+.2f}%" if pd.notna(x) else '—',
                'RSI':       lambda x: f"{x:.1f}"  if pd.notna(x) else '—',
                'VIX':       lambda x: f"{x:.1f}"  if pd.notna(x) else '—',
                'SKEW':      lambda x: f"{x:.1f}"  if pd.notna(x) else '—',
            })
        )
        st.dataframe(styled_summary, use_container_width=True, hide_index=True)
