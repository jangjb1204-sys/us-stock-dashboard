import streamlit as st
import pandas as pd
from stock_analyzer import get_full_analysis, fetch_common_market_data
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="US Stock Dashboard", layout="wide")

st.title("🇺🇸 US Stock 분석 대시보드")

# 사이드바 설정
with st.sidebar:
    st.header("설정")
    ticker_list = {
        'SOXL': 'SOXL', '^GSPC': 'S&P500', '^IXIC': 'NASDAQ',
        'TSLA': 'TESLA', 'QLD': 'QLD', 'NVDA': 'NVIDIA'
    }
    selected_name = st.selectbox("분석할 종목 선택", list(ticker_list.values()))
    selected_ticker = [k for k, v in ticker_list.items() if v == selected_name][0]
    
    period = st.selectbox("조회 기간", ["1y", "2y", "4y"], index=1)
    process_btn = st.button("데이터 분석 시작")

# 데이터 로드 및 출력
if process_btn:
    with st.spinner('데이터를 불러오는 중입니다...'):
        # 1. 공통 시장 지표 수집
        common_data = fetch_common_market_data(period=period)
        
        # 2. 종목 데이터 분석
        df = get_full_analysis(selected_ticker, selected_name, period=period)
        
        if not df.empty:
            # --- 상단 지표 (Metrics) ---
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("현재가", f"${last_row['Close']:.2f}", f"{last_row['Change(%)']}%")
            col2.metric("RSI", last_row['RSI'])
            col3.metric("Fear & Greed", f"{last_row['FG index']} ({last_row['rating']})")
            col4.metric("10Y Treasury", f"{last_row['10Y Treasury']}%")

            # --- 차트 영역 ---
            st.subheader(f"{selected_name} 주가 및 매매 신호")
            
            fig = go.Figure()
            # 캔들스틱
            fig.add_trace(go.Candlestick(
                x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name='Price'
            ))
            # 이평선 추가
            for ma in ['MA20', 'MA60', 'MA120', 'MA200']:
                if ma in df.columns:
                    fig.add_trace(go.Scatter(x=df['Date'], y=df[ma], name=ma, line=dict(width=1.5)))
            
            fig.update_layout(height=600, template='plotly_white', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # --- 데이터 테이블 ---
            st.subheader("최근 분석 데이터 (최근 15일)")
            st.dataframe(df.tail(15).sort_values('Date', ascending=False), use_container_width=True)
            
            # 엑셀 다운로드 기능
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("CSV 결과 다운로드", csv, f"{selected_name}_analysis.csv", "text/csv")
        else:
            st.error("데이터를 가져오지 못했습니다.")