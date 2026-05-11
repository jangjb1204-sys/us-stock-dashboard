import streamlit as st
import pandas as pd
from stock_analyzer import get_full_analysis, fetch_common_market_data
import plotly.graph_objects as go
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="US Stock Dashboard", layout="wide")

# 1시간 동안 데이터를 메모리에 유지 (속도 향상)
@st.cache_data(ttl=3600)
def get_cached_common_data(period):
    return fetch_common_market_data(period)

st.title("🇺🇸 US Stock 분석 대시보드")

# 사이드바 설정
with st.sidebar:
    st.header("🔍 분석 설정")
    ticker_list = {
        'SOXL': 'SOXL (반도체 3x)', 
        '^GSPC': 'S&P500 (시장)', 
        '^IXIC': 'NASDAQ (기술주)',
        'TSLA': 'TESLA (테슬라)', 
        'QLD': 'QLD (나스닥 2x)', 
        'NVDA': 'NVIDIA (엔비디아)',
        'TQQQ': 'TQQQ (나스닥 3x)',
        'AAPL': 'APPLE (애플)'
    }
    selected_name = st.selectbox("분석할 종목 선택", list(ticker_list.values()))
    selected_ticker = [k for k, v in ticker_list.items() if v == selected_name][0]
    
    period = st.selectbox("데이터 조회 기간", ["1y", "2y", "4y", "5y"], index=1)
    process_btn = st.button("실시간 데이터 분석 시작")

# 실행 로직
if process_btn:
    with st.spinner('시장 지표 및 주가 데이터를 분석 중입니다...'):
        # 1. 공통 시장 지표 수집 (VIX, Fear & Greed 등)
        common_data = get_cached_common_data(period)
        
        # 2. 개별 종목 상세 분석 (인자 4개 전달: ticker, name, common_data, period)
        df = get_full_analysis(selected_ticker, selected_name, common_data, period=period)
        
        if not df.empty:
            # --- 상단 주요 지표 (Metrics) ---
            last_row = df.iloc[-1]
            
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("현재가", f"${last_row['Close']:.2f}", f"{last_row['Change(%)']}%")
            with m2:
                rsi_val = last_row['RSI']
                rsi_color = "inverse" if rsi_val >= 70 or rsi_val <= 30 else "normal"
                st.metric("RSI (14)", rsi_val)
            with m3:
                fg_val = last_row.get('FG index', 'N/A')
                fg_rating = last_row.get('rating', '')
                st.metric("Fear & Greed", f"{fg_val}", fg_rating)
            with m4:
                treasury = last_row.get('10Y Treasury', 'N/A')
                st.metric("미 국채 10년물", f"{treasury}%")

            # --- 메인 차트 (Plotly) ---
            st.subheader(f"📈 {selected_name} 주가 및 기술적 지표")
            
            fig = go.Figure()
            
            # 캔들스틱 차트
            fig.add_trace(go.Candlestick(
                x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name='Price'
            ))
            
            # 이동평균선 추가
            for ma in ['MA20', 'MA60', 'MA120', 'MA200']:
                if ma in df.columns:
                    fig.add_trace(go.Scatter(x=df['Date'], y=df[ma], name=ma, line=dict(width=1.5), opacity=0.7))
            
            # 레이아웃 설정
            fig.update_layout(
                height=600, 
                template='plotly_white', 
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- 분석 데이터 상세 테이블 ---
            col_a, col_b = st.columns([2, 1])
            
            with col_a:
                st.subheader("📋 상세 분석 데이터 (최근 15일)")
                # 필요한 컬럼만 필터링하여 출력
                display_cols = ['Date', 'Close', 'Change(%)', 'RSI', 'FG index', 'FG/RSI signal', 'Puddle', 'VIX1D>VIX']
                existing_display_cols = [c for c in display_cols if c in df.columns]
                st.dataframe(df[existing_display_cols].tail(15).sort_values('Date', ascending=False), use_container_width=True)

            with col_b:
                st.subheader("🔔 실시간 매매 신호")
                latest_puddle = last_row.get('Puddle', '')
                latest_sig = last_row.get('FG/RSI signal', '')
                
                if latest_puddle:
                    st.warning(f"**Puddle 신호:** {latest_puddle}")
                else:
                    st.info("현재 특이한 Puddle 신호가 없습니다.")
                
                st.success(f"**현재 매수 강도:** {latest_sig}")
                
                # 다운로드 버튼
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📊 분석 데이터 CSV 다운로드",
                    data=csv,
                    file_name=f"{selected_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv',
                )
        else:
            st.error("데이터 분석에 실패했습니다. 티커를 확인하거나 잠시 후 다시 시도해주세요.")