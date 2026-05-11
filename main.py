import streamlit as st
import pandas as pd
import numpy as np
from stock_analyzer import get_full_analysis, fetch_common_market_data
import plotly.graph_objects as go

st.set_page_config(page_title="US Stock Dashboard", layout="wide")

@st.cache_data(ttl=3600)
def get_cached_common_data(period):
    return fetch_common_market_data(period)

st.title("🇺🇸 US Stock 분석 대시보드")

with st.sidebar:
    st.header("🔍 설정")
    ticker_list = {
        'SOXL': 'SOXL', '^GSPC': 'S&P500', '^IXIC': 'NASDAQ',
        'SSO': 'SSO', 'QLD': 'QLD', 'GLD': 'GOLD',
        'BTGD': 'BTGD', 'SLV': 'SILVER', 'KORU': 'KORU', 'TSLA': 'TESLA'
    }
    selected_name = st.selectbox("종목 선택", list(ticker_list.values()))
    selected_ticker = [k for k, v in ticker_list.items() if v == selected_name][0]
    period = st.selectbox("기간", ["1y", "2y", "4y", "5y"], index=1)
    process_btn = st.button("분석 시작")

if process_btn:
    with st.spinner('실시간 분석 중...'):
        common_data = get_cached_common_data(period)
        df = get_full_analysis(selected_ticker, selected_name, common_data, period=period)
        
        if not df.empty:
            last_row = df.iloc[-1]
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.metric("현재가", f"${last_row['Close']:.2f}")
            with m2: st.metric("RSI", f"{last_row['RSI']:.2f}")
            with m3: 
                fg = last_row.get('FG index', np.nan)
                st.metric("Fear & Greed", f"{int(fg)}" if pd.notna(fg) else "N/A")
            with m4:
                tr = last_row.get('Treasury', np.nan)
                st.metric("미 국채 10년물", f"{tr:.2f}%" if pd.notna(tr) else "로딩 실패")

            # --- 차트 ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name='Price', line=dict(color='#1A1A1B', width=2)))
            
            ma_colors = {'MA20': '#2980B9', 'MA60': '#D35400', 'MA120': '#C0392B', 'MA200': '#8E44AD'}
            for ma, col in ma_colors.items():
                if ma in df.columns:
                    fig.add_trace(go.Scatter(x=df['Date'], y=df[ma], name=ma, line=dict(color=col, width=1.5), opacity=0.6))
            
            # VIX 수직선
            if 'VIX1D' in df.columns and 'VIX' in df.columns:
                vix_buys = df[(pd.to_numeric(df['VIX'], errors='coerce') >= 25) & 
                              (pd.to_numeric(df['VIX1D'], errors='coerce') > pd.to_numeric(df['VIX'], errors='coerce'))]
                for v_date in vix_buys['Date']:
                    fig.add_vline(x=v_date, line_width=2, line_color="#FF0000", opacity=0.3)

            fig.update_layout(height=600, template='plotly_white', hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
            
            # --- 테이블 ---
            st.subheader("📋 최근 분석 상세 (15일)")
            display_df = df[['Date', 'Close', 'RSI', 'FG index', 'FG/RSI signal', 'Puddle']].tail(15).copy()
            st.dataframe(display_df.sort_values('Date', ascending=False).set_index('Date'), use_container_width=True)
        else:
            st.error("데이터 로드 실패")