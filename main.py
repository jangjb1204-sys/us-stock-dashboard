import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

st.set_page_config(page_title="US Stock Analyzer", page_icon="📈", layout="wide")

st.title("🧠 US Stock Multi-Signal Analyzer")
st.markdown("**Fear & Greed + RSI + Puddle + VIX 전략 대시보드**")

st.sidebar.header("설정")

ticker_configs = {
    'SOXL': 'SOXL (3x 반도체)', '^GSPC': 'S&P 500', '^IXIC': 'NASDAQ',
    'SSO': 'SSO (2x S&P)', 'QLD': 'QLD (2x NASDAQ)', 'TSLA': 'TESLA',
    'GLD': 'Gold', 'SLV': 'Silver'
}

selected_tickers = st.sidebar.multiselect(
    "분석할 종목 선택", 
    options=list(ticker_configs.keys()),
    default=['SOXL', '^GSPC', 'TSLA'],
    format_func=lambda x: ticker_configs[x]
)

if st.sidebar.button("🚀 데이터 새로 분석하기", type="primary"):
    with st.spinner("분석 중입니다... (최대 2~3분 소요)"):
        try:
            from stock_analyzer import fetch_common_market_data, process_stock_data, get_ticker_configs
            
            common_data = fetch_common_market_data(period='4y')
            results = {}
            
            progress_bar = st.progress(0)
            for i, ticker in enumerate(selected_tickers):
                name = ticker_configs.get(ticker, ticker)
                st.write(f"🔄 {ticker} ({name}) 분석 중...")
                
                df = process_stock_data(ticker, name, common_data, period='4y', delta=600)
                results[ticker] = df
                
                progress_bar.progress((i + 1) / len(selected_tickers))
                time.sleep(1)
            
            st.success("✅ 모든 분석이 완료되었습니다!")
            st.session_state['results'] = results  # 화면에 유지하기 위해 저장
            
        except Exception as e:
            st.error(f"오류 발생: {e}")

# ==================== 결과 표시 ====================
if 'results' in st.session_state:
    results = st.session_state['results']
    
    tab1, tab2 = st.tabs(["📋 전체 요약", "🔍 종목 상세 분석"])
    
    with tab1:
        st.header("최근 분석 결과 요약")
        for ticker, df in results.items():
            if not df.empty:
                name = ticker_configs.get(ticker, ticker)
                st.subheader(f"{name} ({ticker})")
                st.dataframe(df.tail(10), use_container_width=True)
                st.divider()
    
    with tab2:
        st.header("종목 상세 분석")
        ticker_choice = st.selectbox("종목 선택", options=list(results.keys()))
        
        if ticker_choice in results:
            df = results[ticker_choice]
            name = ticker_configs.get(ticker_choice, ticker_choice)
            
            st.subheader(f"{name} ({ticker_choice}) - 최근 데이터")
            st.dataframe(df, use_container_width=True)
            
            # 간단 차트 추가
            if not df.empty and 'Close' in df.columns and 'Date' in df.columns:
                st.subheader("가격 추이")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], mode='lines+markers', name='Close'))
                if 'MA20' in df.columns:
                    fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], mode='lines', name='MA20'))
                if 'MA60' in df.columns:
                    fig.add_trace(go.Scatter(x=df['Date'], y=df['MA60'], mode='lines', name='MA60'))
                
                fig.update_layout(height=500, title=f"{name} 가격 및 이동평균")
                st.plotly_chart(fig, use_container_width=True)
                
                # RSI 차트
                if 'RSI' in df.columns:
                    st.subheader("RSI")
                    rsi_fig = go.Figure()
                    rsi_fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], mode='lines', name='RSI'))
                    rsi_fig.add_hline(y=30, line_dash="dash", line_color="green")
                    rsi_fig.add_hline(y=70, line_dash="dash", line_color="red")
                    rsi_fig.update_layout(height=300)
                    st.plotly_chart(rsi_fig, use_container_width=True)
else:
    st.info("왼쪽 사이드바에서 '데이터 새로 분석하기' 버튼을 눌러주세요.")

st.caption("Developed for personal use")