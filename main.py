import streamlit as st
import pandas as pd
from stock_analyzer import get_full_analysis, fetch_common_market_data
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(page_title="US Stock Dash", layout="wide")

@st.cache_data(ttl=3600)
def get_cached_common_data(period):
    return fetch_common_market_data(period)

st.title("🇺🇸 US Stock 분석 대시보드 (With Signal)")

# 사이드바
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
    with st.spinner('시장 데이터를 분석 중입니다...'):
        common_data = get_cached_common_data(period)
        df = get_full_analysis(selected_ticker, common_data, period=period)
        
        if not df.empty:
            # 1. 상단 지표
            last = df.iloc[-1]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("현재가", f"${last['Close']:.2f}")
            m2.metric("RSI (14)", f"{last['RSI']}")
            m3.metric("Fear & Greed", f"{int(last.get('FG index', 50))}")
            m4.metric("10Y Treasury", f"{last.get('Treasury', 0):.2f}%")

            # 2. 메인 차트 (라인 + 신호)
            fig = go.Figure()
            
            # 주가 라인
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name='Price', line=dict(color='#1A1A1B', width=2.5)))
            
            # 이평선
            for ma, col in {'MA20': '#2980B9', 'MA60': '#D35400', 'MA120': '#C0392B', 'MA200': '#8E44AD'}.items():
                if ma in df.columns:
                    fig.add_trace(go.Scatter(x=df['Date'], y=df[ma], name=ma, line=dict(color=col, width=1.5), opacity=0.7))

            # VIX 매수 신호 (빨간 실선)
            if 'VIX1D>VIX' in df.columns:
                vix_buys = df[df['VIX1D>VIX'] == 'BUY']
                for v_date in vix_buys['Date']:
                    fig.add_vline(x=v_date, line_width=2, line_color="#FF0000", opacity=0.4)

            # Puddle 신호 (초록 삼각형)
            p_df = df[df['Puddle'].astype(str).str.len() > 1].copy()
            if not p_df.empty:
                fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df['Low']*0.96, mode='markers', name='Puddle Buy',
                    marker=dict(symbol='triangle-up', size=14, color='#00FF00', line=dict(width=2, color='#004d00')),
                    text=p_df['Puddle'], hovertemplate="<b>%{text}</b><br>%{x}"))

            # RSI 과매도 (파란 원)
            oversold = df[df['RSI'] <= 30]
            if not oversold.empty:
                fig.add_trace(go.Scatter(x=oversold['Date'], y=oversold['Close'], mode='markers', name='RSI Low',
                    marker=dict(symbol='circle', size=10, color='#3498DB', line=dict(width=2, color='#1A5276'))))

            fig.update_layout(height=650, template='plotly_white', hovermode='x unified', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # 3. 데이터 테이블
            st.subheader("📋 최근 분석 데이터 (15일)")
            # 날짜를 문자열로 변환하여 시간 제거
            display_df = df[['Date', 'Close', 'RSI', 'FG index', 'FG/RSI signal', 'Puddle']].tail(15).copy()
            display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
            st.dataframe(display_df.sort_values('Date', ascending=False).set_index('Date'), use_container_width=True)
            
            # 엑셀 다운로드 버튼
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📊 전체 분석 데이터 다운로드(CSV)", csv, f"{selected_name}_data.csv", "text/csv")