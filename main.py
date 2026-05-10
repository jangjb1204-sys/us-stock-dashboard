import streamlit as st
import pandas as pd
import os
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="US Stock Analyzer", page_icon="📈", layout="wide")

st.title("🧠 US Stock Multi-Signal Analyzer")
st.markdown("**Fear & Greed + RSI + Stochastic + Puddle + VIX 전략 종합 대시보드**")

st.sidebar.header("⚙️ 설정")

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
    with st.spinner("데이터 수집 및 분석 중... (2~4분 소요)"):
        try:
            from stock_analyzer import fetch_common_market_data, process_stock_data, get_ticker_configs
            
            common_data = fetch_common_market_data(period='4y')
            results = {}
            
            progress_bar = st.progress(0)
            for i, ticker in enumerate(selected_tickers):
                name = ticker_configs.get(ticker, ticker)
                st.write(f"🔄 {ticker} 분석 중...")
                df = process_stock_data(ticker, name, common_data, period='4y', delta=600)
                results[ticker] = df
                progress_bar.progress((i + 1) / len(selected_tickers))
                time.sleep(1.5)
            
            st.success("✅ 분석 완료!")
            st.session_state['results'] = results
            
        except Exception as e:
            st.error(f"오류 발생: {e}")

# ====================== 결과 표시 ======================
if 'results' in st.session_state:
    results = st.session_state['results']
    
    tab1, tab2 = st.tabs(["📊 전체 종합 요약", "🔍 종목 상세 분석"])

    with tab1:
        st.header("📋 전체 종목 요약")
        summary_data = []
        for ticker, df in results.items():
            if not df.empty:
                latest = df.iloc[-1]
                summary_data.append({
                    '종목': ticker_configs.get(ticker, ticker),
                    '현재가': latest.get('Close', 'N/A'),
                    '변동률': latest.get('Change(%)', 'N/A'),
                    'RSI': latest.get('RSI', 'N/A'),
                    'FG Index': latest.get('FG index', 'N/A'),
                    'FG/RSI Signal': latest.get('FG/RSI signal', 'N/A'),
                    '최근 업데이트': latest.get('Date', 'N/A')
                })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, height=400)
    
    with tab2:
        st.header("🔍 종목 상세 분석")
        ticker_choice = st.selectbox("상세히 보고 싶은 종목 선택", options=list(results.keys()))
        
        if ticker_choice in results:
            df = results[ticker_choice]
            name = ticker_configs.get(ticker_choice, ticker_choice)
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader(f"{name} ({ticker_choice})")
                st.dataframe(df.tail(15), use_container_width=True)
            
            with col2:
                if not df.empty and 'Close' in df.columns:
                    st.subheader("가격 추이 + 이동평균")
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name='Close', line=dict(width=2.5)))
                    for ma in ['MA20', 'MA60', 'MA120', 'MA200']:
                        if ma in df.columns:
                            fig.add_trace(go.Scatter(x=df['Date'], y=df[ma], name=ma))
                    
                    fig.update_layout(height=500, title=f"{name} 가격 추이")
                    st.plotly_chart(fig, use_container_width=True)
            
            # RSI + Signal
            if 'RSI' in df.columns:
                st.subheader("RSI & 주요 신호")
                rsi_fig = make_subplots(rows=1, cols=1)
                rsi_fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], name='RSI', line=dict(color='purple')))
                rsi_fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
                rsi_fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
                rsi_fig.update_layout(height=350, title="RSI")
                st.plotly_chart(rsi_fig, use_container_width=True)

else:
    st.info("👈 왼쪽 사이드바에서 **'데이터 새로 분석하기'** 버튼을 눌러주세요.")
    
st.caption("💡 분석 버튼을 누른 후 잠시 기다리면 테이블과 차트가 모두 표시됩니다.")