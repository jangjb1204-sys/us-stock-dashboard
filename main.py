import streamlit as st
import pandas as pd
from stock_analyzer import get_full_analysis, fetch_common_market_data
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="US Stock Insight", layout="wide")

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
    with st.spinner('데이터를 분석 중입니다...'):
        common_data = get_cached_common_data(period)
        df = get_full_analysis(selected_ticker, selected_name, common_data, period=period)
        
        if not df.empty:
            last_row = df.iloc[-1]
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.metric("현재가", f"${last_row['Close']:.2f}", f"{last_row.get('Change(%)', 0)}%")
            with m2: st.metric("RSI", last_row['RSI'])
            with m3: st.metric("Fear & Greed", f"{last_row.get('FG index', 'N/A')}", last_row.get('rating', ''))
            with m4: st.metric("미 국채 10년물", f"{last_row.get('Treasury', 0):.2f}%")

            # --- 차트 시각화 ---
            fig = go.Figure()
            # 주가 실선
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name='Price', line=dict(color='#1A1A1B', width=2.5)))
            
            # 이평선 (선명도 강화)
            colors = {'MA20': '#2980B9', 'MA60': '#D35400', 'MA120': '#C0392B', 'MA200': '#8E44AD'}
            for ma, col in colors.items():
                if ma in df.columns:
                    fig.add_trace(go.Scatter(x=df['Date'], y=df[ma], name=ma, line=dict(color=col, width=1.8), opacity=0.7))
            
            # VIX 매수 신호 (빨간 실선)
            if 'VIX1D>VIX' in df.columns:
                vix_buys = df[df['VIX1D>VIX'] == 'BUY']
                for v_date in vix_buys['Date']:
                    fig.add_vline(x=v_date, line_width=2, line_color="#FF0000", opacity=0.5)

            # Puddle 신호 (삼각형 마커)
            p_df = df[df['Puddle'].astype(str).str.len() > 1].copy()
            if not p_df.empty:
                fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df['Low']*0.95, mode='markers', name='Puddle',
                    marker=dict(symbol='triangle-up', size=16, color='#00FF00', line=dict(width=2, color='#004d00')),
                    text=p_df['Puddle'], hovertemplate="<b>%{text}</b><br>%{x}<extra></extra>"))

            # RSI 과매도 (블루 서클)
            temp_rsi = pd.to_numeric(df['RSI'], errors='coerce')
            oversold = df[temp_rsi <= 30]
            if not oversold.empty:
                fig.add_trace(go.Scatter(x=oversold['Date'], y=oversold['Close'], mode='markers', name='RSI Low',
                    marker=dict(symbol='circle', size=10, color='#3498DB', line=dict(width=2, color='#1A5276'))))

            fig.update_layout(height=700, template='plotly_white', hovermode='x unified', xaxis_rangeslider_visible=False,
                              legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"))
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("📋 데이터 상세 (최근 15일)")
            st.dataframe(df[['Date', 'Close', 'RSI', 'FG index', 'FG/RSI signal', 'Puddle']].tail(15).sort_values('Date', ascending=False), use_container_width=True)