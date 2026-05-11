import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from stock_analyzer import StockAnalyzer
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="US Stock Dashboard", layout="wide")

# 분석기 인스턴스 생성
@st.cache_resource
def get_analyzer():
    return StockAnalyzer()

analyzer = get_analyzer()

st.title("🚀 US Stock Real-time Analysis Dashboard")

# 사이드바 설정
with st.sidebar:
    st.header("Search Options")
    ticker = st.text_input("Enter Ticker", value="SOXL").upper()
    period = st.selectbox("Data Period", ['1y', '2y', '4y'], index=1)
    view_days = st.slider("Display Range (Days)", 30, 600, 300)

# 데이터 로드 (캐싱 활용)
@st.cache_data(ttl=3600)
def load_full_data(ticker, period):
    stock_df = yf.Ticker(ticker).history(period=period).reset_index()
    stock_df['Date'] = pd.to_datetime(stock_df['Date'].dt.date)
    
    # 지표 계산
    stock_df = analyzer.calculate_metrics(stock_df)
    
    # 시장 데이터 병합
    market_df = analyzer.get_market_indicators(period)
    fg_df = analyzer.fetch_fear_and_greed()
    
    final_df = pd.merge(stock_df, market_df, on='Date', how='left')
    if not fg_df.empty:
        final_df = pd.merge(final_df, fg_df, on='Date', how='left')
    
    # VIX 신호 생성
    if 'VIX' in final_df.columns and 'VIX1D' in final_df.columns:
        final_df['VIX_Signal'] = (final_df['VIX'] >= 25) & (final_df['VIX1D'] > final_df['VIX'])
    
    return final_df

try:
    df = load_full_data(ticker, period)
    recent_df = df.tail(view_days)

    # 1. 상단 지표 (Metrics)
    last_row = df.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"${last_row['Close']:.2f}", f"{last_row['Change(%)']}%")
    col2.metric("RSI (14)", last_row['RSI'])
    col3.metric("Fear & Greed", f"{last_row.get('FG index', 'N/A')}", last_row.get('rating', ''))
    col4.metric("10Y Treasury", f"{last_row.get('10Y Treasury', 'N/A')}%")

    # 2. 메인 인터랙티브 차트 (Plotly)
    st.subheader(f"Technical Analysis: {ticker}")
    fig = go.Figure()

    # 캔들스틱 차트
    fig.add_trace(go.Candlestick(x=recent_df['Date'], open=recent_df['Open'], high=recent_df['High'],
                                 low=recent_df['Low'], close=recent_df['Close'], name='Price'))

    # 이동평균선
    for ma in ['MA20', 'MA60', 'MA120', 'MA200']:
        fig.add_trace(go.Scatter(x=recent_df['Date'], y=recent_df[ma], name=ma, line=dict(width=1.5), opacity=0.7))

    # Puddle Buy 신호 표시
    puddle_points = recent_df[recent_df['Puddle'] != '']
    fig.add_trace(go.Scatter(x=puddle_points['Date'], y=puddle_points['Low'] * 0.97, mode='markers',
                             marker=dict(symbol='triangle-up', size=12, color='red'), name='Puddle Signal'))

    fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # 3. 데이터 테이블
    st.subheader("Recent Indicators Table")
    display_cols = ['Date', 'Close', 'Change(%)', 'RSI', 'FG index', 'Puddle', 'VIX', 'SKEW']
    actual_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(recent_df[actual_cols].sort_values('Date', ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")