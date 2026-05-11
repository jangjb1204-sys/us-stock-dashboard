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
    initial_sidebar_state="expanded",
)

# ── 스타일 ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp { background-color: #0e1117; }

    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border-right: 1px solid #30363d;
    }

    /* 메트릭 카드 */
    div[data-testid="metric-container"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 12px 16px;
    }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #161b22;
        border-radius: 8px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 6px;
        color: #8b949e;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: #238636 !important;
        color: white !important;
    }

    /* 데이터프레임 헤더 */
    .dataframe thead tr th {
        background-color: #161b22 !important;
        color: #58a6ff !important;
        font-weight: 700;
    }

    /* 신호 배지 */
    .signal-buy   { color: #3fb950; font-weight: 700; }
    .signal-sell  { color: #f85149; font-weight: 700; }
    .signal-stop  { color: #d29922; font-weight: 700; }

    h1, h2, h3 { color: #e6edf3 !important; }
    p, li       { color: #8b949e; }

    /* 로딩 스피너 색상 */
    .stSpinner > div { border-top-color: #238636 !important; }

    div[data-testid="stSelectbox"] label,
    div[data-testid="stSlider"] label { color: #8b949e !important; }
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

# ── 캐싱 ───────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)   # 30분 캐시
def load_common_data(period: str) -> dict:
    return fetch_common_market_data(period=period)


@st.cache_data(ttl=1800, show_spinner=False)
def load_ticker_data(ticker: str, name: str, period: str, delta: int, _cache_key: str) -> pd.DataFrame:
    common = load_common_data(period)
    return process_stock_data(ticker, name, common, period=period, delta=delta)


# ── 차트 함수 ──────────────────────────────────────────────────────────────────
def build_candlestick_chart(df: pd.DataFrame, name: str) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.60, 0.20, 0.20],
        vertical_spacing=0.03,
    )

    # 캔들스틱
    fig.add_trace(go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name='Price',
        increasing_line_color='#3fb950', increasing_fillcolor='#3fb950',
        decreasing_line_color='#f85149', decreasing_fillcolor='#f85149',
    ), row=1, col=1)

    # 이동평균선
    for ma, color in MA_COLORS.items():
        if ma in df.columns and df[ma].notna().any():
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df[ma], name=ma,
                line=dict(color=color, width=1.5), mode='lines',
            ), row=1, col=1)

    # Puddle 신호 삼각형
    if 'Puddle' in df.columns:
        puddle_df = df[df['Puddle'].str.contains(r'[a-zA-Z]', na=False)]
        if not puddle_df.empty:
            fig.add_trace(go.Scatter(
                x=puddle_df['Date'],
                y=puddle_df['Low'] * 0.982,
                mode='markers',
                name='Puddle Signal',
                marker=dict(symbol='triangle-up', size=10, color='#ff7b72',
                            line=dict(width=1, color='white')),
            ), row=1, col=1)

    # VIX1D > VIX 수직선
    if 'VIX1D>VIX' in df.columns:
        buy_dates = df[df['VIX1D>VIX'] == 'BUY']['Date']
        for d in buy_dates:
            fig.add_vline(x=d, line=dict(color='rgba(255,123,114,0.35)', width=1), row=1, col=1)

    # RSI 패널
    if 'RSI' in df.columns and df['RSI'].notna().any():
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['RSI'], name='RSI',
            line=dict(color='#d2a679', width=1.5),
        ), row=2, col=1)
        fig.add_hline(y=70, line=dict(color='#f85149', width=1, dash='dot'), row=2, col=1)
        fig.add_hline(y=30, line=dict(color='#3fb950', width=1, dash='dot'), row=2, col=1)
        fig.update_yaxes(title_text='RSI', range=[0, 100], row=2, col=1,
                         tickfont=dict(color='#8b949e'), titlefont=dict(color='#8b949e'))

    # VIX 패널
    if 'VIX' in df.columns and df['VIX'].notna().any():
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['VIX'], name='VIX',
            line=dict(color='#79c0ff', width=1.5), fill='tozeroy',
            fillcolor='rgba(121,192,255,0.08)',
        ), row=3, col=1)
        fig.add_hline(y=25, line=dict(color='#3fb950', width=1, dash='dot'), row=3, col=1)
        fig.update_yaxes(title_text='VIX', row=3, col=1,
                         tickfont=dict(color='#8b949e'), titlefont=dict(color='#8b949e'))

    fig.update_layout(
        title=dict(text=f'<b>{name}</b> — Candlestick', x=0.02,
                   font=dict(size=18, color='#e6edf3')),
        plot_bgcolor='#0d1117', paper_bgcolor='#0d1117',
        font=dict(family='monospace', color='#8b949e'),
        legend=dict(orientation='h', yanchor='bottom', y=1.01,
                    xanchor='left', x=0, font=dict(size=11),
                    bgcolor='rgba(0,0,0,0)', bordercolor='#30363d'),
        xaxis_rangeslider_visible=False,
        height=650,
        margin=dict(l=60, r=20, t=60, b=40),
    )
    for row in [1, 2, 3]:
        fig.update_xaxes(showgrid=True, gridcolor='#21262d', zeroline=False, row=row, col=1)
        fig.update_yaxes(showgrid=True, gridcolor='#21262d', zeroline=False, row=row, col=1)

    return fig


def build_line_chart(df: pd.DataFrame, name: str) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.70, 0.30], vertical_spacing=0.04)

    # 주가 라인
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Close'], name=f'{name} Close',
        line=dict(color='#e6edf3', width=2),
    ), row=1, col=1)

    # 이동평균선
    for ma, color in MA_COLORS.items():
        if ma in df.columns and df[ma].notna().any():
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df[ma], name=ma,
                line=dict(color=color, width=1.2, dash='dot'),
            ), row=1, col=1)

    # VIX1D > VIX 수직선
    if 'VIX1D>VIX' in df.columns:
        buy_dates = df[df['VIX1D>VIX'] == 'BUY']['Date']
        for d in buy_dates:
            fig.add_vline(x=d, line=dict(color='rgba(248,81,73,0.4)', width=1), row=1, col=1)

    # RSI & Puddle 겹치는 지점 강조
    if 'RSI' in df.columns and 'Puddle' in df.columns:
        oversold  = df[df['RSI'] <= 30]
        puddle_df = df[df['Puddle'].str.contains(r'[a-zA-Z]', na=False)]
        overlap   = pd.merge(oversold, puddle_df, on='Date', how='inner')
        if not overlap.empty:
            fig.add_trace(go.Scatter(
                x=overlap['Date'], y=overlap['Close_x'],
                mode='markers', name='RSI & Puddle',
                marker=dict(symbol='circle', size=10, color='#bc8cff',
                            line=dict(width=1.5, color='white')),
            ), row=1, col=1)

    # Fear & Greed 패널
    if 'FG index' in df.columns and df['FG index'].notna().any():
        fg_df = df[df['FG index'].notna()]
        fig.add_trace(go.Bar(
            x=fg_df['Date'], y=fg_df['FG index'],
            name='Fear & Greed',
            marker=dict(
                color=fg_df['FG index'],
                colorscale=[[0, '#f85149'], [0.5, '#d29922'], [1, '#3fb950']],
                cmin=0, cmax=100,
            ),
        ), row=2, col=1)
        fig.add_hline(y=50, line=dict(color='#58a6ff', width=1, dash='dot'), row=2, col=1)
        fig.update_yaxes(title_text='F&G', range=[0, 100], row=2, col=1,
                         tickfont=dict(color='#8b949e'), titlefont=dict(color='#8b949e'))

    fig.update_layout(
        title=dict(text=f'<b>{name}</b> — Line + Signals', x=0.02,
                   font=dict(size=18, color='#e6edf3')),
        plot_bgcolor='#0d1117', paper_bgcolor='#0d1117',
        font=dict(family='monospace', color='#8b949e'),
        legend=dict(orientation='h', yanchor='bottom', y=1.01,
                    xanchor='left', x=0, font=dict(size=11),
                    bgcolor='rgba(0,0,0,0)', bordercolor='#30363d'),
        height=580,
        margin=dict(l=60, r=20, t=60, b=40),
    )
    for row in [1, 2]:
        fig.update_xaxes(showgrid=True, gridcolor='#21262d', zeroline=False, row=row, col=1)
        fig.update_yaxes(showgrid=True, gridcolor='#21262d', zeroline=False, row=row, col=1)

    return fig


# ── 컬러 데이터프레임 ───────────────────────────────────────────────────────────
def style_table(df: pd.DataFrame) -> pd.DataFrame.style:
    display_cols = [
        'Date', 'Close', 'Change(%)', '2sigma(%)',
        'RSI', 'FG index', 'FG/RSI signal', 'SS Signal',
        'Puddle', 'VIX', 'VIX1D', 'VIX1D>VIX', 'SKEW', '10Y Treasury'
    ]
    existing = [c for c in display_cols if c in df.columns]
    sub = df[existing].tail(30).copy()
    if 'Date' in sub.columns:
        sub['Date'] = pd.to_datetime(sub['Date']).dt.strftime('%Y-%m-%d')

    def color_row(row):
        styles = [''] * len(row)
        idx = list(row.index)

        def si(col):
            return idx.index(col) if col in idx else -1

        # Change(%) 색상
        ci = si('Change(%)')
        if ci >= 0 and row.iloc[ci] != '' and pd.notna(row.iloc[ci]):
            try:
                v = float(row.iloc[ci])
                styles[ci] = 'color: #f85149' if v < 0 else 'color: #3fb950' if v > 0 else ''
            except Exception:
                pass

        # 2sigma 배경 (Change < -2sigma → 노란 배경)
        cci = si('Change(%)')
        sci = si('2sigma(%)')
        if cci >= 0 and sci >= 0:
            try:
                chg = float(row.iloc[cci]) if pd.notna(row.iloc[cci]) else 0
                sig = float(row.iloc[sci]) if pd.notna(row.iloc[sci]) else 0
                if chg < -sig:
                    styles = ['background-color: rgba(210,153,34,0.25)'] * len(styles)
            except Exception:
                pass

        # RSI
        ri = si('RSI')
        if ri >= 0 and pd.notna(row.iloc[ri]) and row.iloc[ri] != '':
            try:
                v = float(row.iloc[ri])
                styles[ri] = 'color: #3fb950' if v <= 30 else 'color: #f85149' if v >= 70 else ''
            except Exception:
                pass

        # VIX
        vi = si('VIX')
        if vi >= 0 and pd.notna(row.iloc[vi]) and row.iloc[vi] != '':
            try:
                if float(row.iloc[vi]) > 25:
                    styles[vi] = 'color: #3fb950'
            except Exception:
                pass

        # SKEW
        ski = si('SKEW')
        if ski >= 0 and pd.notna(row.iloc[ski]) and row.iloc[ski] != '':
            try:
                v = float(row.iloc[ski])
                styles[ski] = 'color: #f85149' if v >= 155 else 'color: #3fb950' if v <= 127 else ''
            except Exception:
                pass

        return styles

    return sub.style.apply(color_row, axis=1)


# ── 사이드바 ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 US Stock Dashboard")
    st.markdown("---")

    ticker_labels = {v: k for k, v in TICKER_CONFIGS.items()}   # name → ticker
    all_names = list(TICKER_CONFIGS.values())

    selected_name = st.selectbox("📌 종목 선택", all_names, index=0)
    selected_ticker = ticker_labels[selected_name]

    st.markdown("---")
    period_label = st.select_slider("📅 데이터 기간", options=list(PERIOD_OPTIONS.keys()), value="2년")
    period = PERIOD_OPTIONS[period_label]

    delta_label = st.select_slider("🔍 표시 범위", options=list(DELTA_OPTIONS.keys()), value="180일")
    delta = DELTA_OPTIONS[delta_label]

    st.markdown("---")
    refresh = st.button("🔄 데이터 새로고침", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption(f"⏱ 마지막 업데이트\n{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption("캐시 유효시간: 30분")


# ── 메인 영역 ──────────────────────────────────────────────────────────────────
st.markdown(f"# 📈 {selected_name} `{selected_ticker}`")
st.markdown("---")

cache_key = f"{period}_{delta}"
with st.spinner(f"{selected_name} 데이터 불러오는 중..."):
    df = load_ticker_data(selected_ticker, selected_name, period, delta, cache_key)

if df.empty:
    st.error(f"❌ {selected_ticker} 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

latest = df.iloc[-1]
prev   = df.iloc[-2] if len(df) >= 2 else latest

# ── 요약 메트릭 카드 ────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5, col6 = st.columns(6)

def safe_float(val):
    try:
        return float(val)
    except Exception:
        return None

close_val  = safe_float(latest.get('Close'))
change_val = safe_float(latest.get('Change(%)'))
rsi_val    = safe_float(latest.get('RSI'))
vix_val    = safe_float(latest.get('VIX'))
fg_val     = safe_float(latest.get('FG index'))
skew_val   = safe_float(latest.get('SKEW'))

with col1:
    delta_str = f"{change_val:+.2f}%" if change_val is not None else "N/A"
    st.metric("💰 종가", f"${close_val:.2f}" if close_val else "N/A", delta_str)

with col2:
    rsi_status = ""
    if rsi_val:
        rsi_status = "🟢 과매도" if rsi_val <= 30 else "🔴 과매수" if rsi_val >= 70 else "⚪ 중립"
    st.metric("📊 RSI", f"{rsi_val:.1f}" if rsi_val else "N/A", rsi_status)

with col3:
    vix_status = "🟢 높음" if vix_val and vix_val > 25 else ""
    st.metric("😨 VIX", f"{vix_val:.1f}" if vix_val else "N/A", vix_status)

with col4:
    fg_status = ""
    if fg_val is not None:
        fg_status = "극도 탐욕" if fg_val >= 75 else "탐욕" if fg_val >= 55 else "중립" if fg_val >= 45 else "공포" if fg_val >= 25 else "극도 공포"
    st.metric("🎭 F&G", f"{fg_val:.0f}" if fg_val is not None else "N/A", fg_status)

with col5:
    skew_status = "🔴 고위험" if skew_val and skew_val >= 155 else "🟢 저위험" if skew_val and skew_val <= 127 else ""
    st.metric("📐 SKEW", f"{skew_val:.1f}" if skew_val else "N/A", skew_status)

with col6:
    treasury_val = safe_float(latest.get('10Y Treasury'))
    st.metric("🏦 10Y Treasury", f"{treasury_val:.2f}%" if treasury_val else "N/A")

st.markdown("")

# ── 탭 구성 ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🕯️ 캔들스틱 차트", "📉 라인 + 신호 차트", "📋 데이터 테이블"])

with tab1:
    fig_candle = build_candlestick_chart(df, selected_name)
    st.plotly_chart(fig_candle, use_container_width=True)

    # 신호 요약
    st.markdown("### 📌 최근 신호 요약")
    sig_col1, sig_col2, sig_col3 = st.columns(3)

    with sig_col1:
        if 'Puddle' in df.columns:
            recent_puddle = df[df['Puddle'].str.contains(r'[a-zA-Z]', na=False)].tail(3)
            if not recent_puddle.empty:
                st.markdown("**🔴 Puddle 신호**")
                for _, row in recent_puddle.iterrows():
                    st.markdown(f"- {pd.to_datetime(row['Date']).strftime('%Y-%m-%d')} · {row['Puddle']}")
            else:
                st.markdown("**🔴 Puddle 신호**\n\n최근 없음")

    with sig_col2:
        if 'VIX1D>VIX' in df.columns:
            recent_vix = df[df['VIX1D>VIX'] == 'BUY'].tail(3)
            if not recent_vix.empty:
                st.markdown("**🟢 VIX1D > VIX BUY**")
                for _, row in recent_vix.iterrows():
                    st.markdown(f"- {pd.to_datetime(row['Date']).strftime('%Y-%m-%d')}")
            else:
                st.markdown("**🟢 VIX1D > VIX BUY**\n\n최근 없음")

    with sig_col3:
        if 'SS Signal' in df.columns:
            recent_ss = df[df['SS Signal'].isin(['Buy', 'Sell'])].tail(3)
            if not recent_ss.empty:
                st.markdown("**🔵 Stochastic 신호**")
                for _, row in recent_ss.iterrows():
                    emoji = "🟢" if row['SS Signal'] == 'Buy' else "🔴"
                    st.markdown(f"- {pd.to_datetime(row['Date']).strftime('%Y-%m-%d')} · {emoji} {row['SS Signal']}")
            else:
                st.markdown("**🔵 Stochastic 신호**\n\n최근 없음")

with tab2:
    fig_line = build_line_chart(df, selected_name)
    st.plotly_chart(fig_line, use_container_width=True)

    # FG/RSI 신호 분포
    if 'FG/RSI signal' in df.columns:
        st.markdown("### 📊 FG/RSI 신호 분포")
        signal_counts = df['FG/RSI signal'].value_counts().reset_index()
        signal_counts.columns = ['신호', '횟수']
        st.dataframe(signal_counts, hide_index=True, use_container_width=False)

with tab3:
    st.markdown("### 📋 최근 30일 데이터")
    styled = style_table(df)
    st.dataframe(styled, use_container_width=True, height=500)

    # CSV 다운로드
    csv = df.copy()
    if 'Date' in csv.columns:
        csv['Date'] = pd.to_datetime(csv['Date']).dt.strftime('%Y-%m-%d')
    st.download_button(
        label="⬇️ 전체 데이터 CSV 다운로드",
        data=csv.to_csv(index=False, encoding='utf-8-sig'),
        file_name=f"{selected_name}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

# ── 전체 종목 요약 ─────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🗂 전체 종목 최신 현황 (클릭해서 펼치기)", expanded=False):
    summary_rows = []
    prog = st.progress(0, text="전체 종목 데이터 로딩 중...")
    total = len(TICKER_CONFIGS)
    for i, (ticker, name) in enumerate(TICKER_CONFIGS.items()):
        try:
            d = load_ticker_data(ticker, name, period, delta, cache_key)
            if not d.empty:
                lat = d.iloc[-1]
                summary_rows.append({
                    '종목': name,
                    'Ticker': ticker,
                    '종가': safe_float(lat.get('Close')),
                    'Change(%)': safe_float(lat.get('Change(%)')),
                    'RSI': safe_float(lat.get('RSI')),
                    'FG/RSI signal': lat.get('FG/RSI signal', ''),
                    'VIX': safe_float(lat.get('VIX')),
                    'SKEW': safe_float(lat.get('SKEW')),
                })
        except Exception:
            pass
        prog.progress((i + 1) / total, text=f"로딩 중... {name}")
        time.sleep(0.1)
    prog.empty()

    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)

        def highlight_change(val):
            try:
                v = float(val)
                return 'color: #f85149' if v < 0 else 'color: #3fb950' if v > 0 else ''
            except Exception:
                return ''

        def highlight_rsi(val):
            try:
                v = float(val)
                return 'color: #3fb950' if v <= 30 else 'color: #f85149' if v >= 70 else ''
            except Exception:
                return ''

        styled_summary = (
            summary_df.style
            .applymap(highlight_change, subset=['Change(%)'])
            .applymap(highlight_rsi, subset=['RSI'])
            .format({
                '종가': lambda x: f"${x:.2f}" if pd.notna(x) else '',
                'Change(%)': lambda x: f"{x:+.2f}%" if pd.notna(x) else '',
                'RSI': lambda x: f"{x:.1f}" if pd.notna(x) else '',
                'VIX': lambda x: f"{x:.1f}" if pd.notna(x) else '',
                'SKEW': lambda x: f"{x:.1f}" if pd.notna(x) else '',
            })
        )
        st.dataframe(styled_summary, use_container_width=True, hide_index=True)
