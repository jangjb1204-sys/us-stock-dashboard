import streamlit as st
import pandas as pd
from stock_analyzer import get_full_analysis, fetch_common_market_data
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="US Stock Insight Dashboard", layout="wide")

# 2. 데이터 캐싱 (속도 최적화)
@st.cache_data(ttl=3600)
def get_cached_common_data(period):
    return fetch_common_market_data(period)

st.title("🇺🇸 US Stock 분석 대시보드")
st.markdown("신뢰할 수 있는 지표를 바탕으로 한 실시간 매매 신호 분석")

# 3. 사이드바 설정
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

# 4. 실행 로직
if process_btn:
    with st.spinner('차트와 신호를 생성 중입니다...'):
        # 데이터 수집
        common_data = get_cached_common_data(period)
        df = get_full_analysis(selected_ticker, selected_name, common_data, period=period)
        
        if not df.empty:
            # --- 상단 주요 지표 (Metrics) ---
            last_row = df.iloc[-1]
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("현재가", f"${last_row['Close']:.2f}", f"{last_row['Change(%)']}%")
            with m2:
                st.metric("RSI (14)", last_row['RSI'])
            with m3:
                st.metric("Fear & Greed", f"{last_row.get('FG index', 'N/A')}", last_row.get('rating', ''))
            with m4:
                st.metric("미 국채 10년물", f"{last_row.get('10Y Treasury', 'N/A')}%")

            # --- 메인 인터랙티브 차트 (기존 이미지 분석 로직 반영) ---
            st.subheader(f"📈 {selected_name} 주가 및 매매 전략 트렌드")
            
            fig = go.Figure()
            
            # (1) 캔들스틱 차트
            fig.add_trace(go.Candlestick(
                x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name='Price', increasing_line_color='#26A69A', decreasing_line_color='#EF5350'
            ))
            
            # (2) 이동평균선 (MA20, 60, 120, 200)
            ma_colors = {'MA20': '#2196F3', 'MA60': '#FF9800', 'MA120': '#F44336', 'MA200': '#9C27B0'}
            for ma, color in ma_colors.items():
                if ma in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df['Date'], y=df[ma], name=ma, 
                        line=dict(color=color, width=1.3), opacity=0.5
                    ))
            
            # (3) VIX1D > VIX Buy 신호 (수직 점선)
            if 'VIX1D>VIX' in df.columns:
                vix_buys = df[df['VIX1D>VIX'] == 'BUY']
                for v_date in vix_buys['Date']:
                    fig.add_vline(x=v_date, line_width=1, line_dash="dash", line_color="#FF4500", opacity=0.3)

            # (4) Puddle 매수 신호 (초록색 삼각형 마커)
            if 'Puddle' in df.columns:
                # 글자가 포함된 행만 필터링
                puddle_buys = df[df['Puddle'].astype(str).str.len() > 1]
                if not puddle_buys.empty:
                    fig.add_trace(go.Scatter(
                        x=puddle_buys['Date'], y=puddle_buys['Low'] * 0.96,
                        mode='markers', name='Puddle Buy',
                        marker=dict(symbol='triangle-up', size=12, color='#00FF00', line=dict(width=1)),
                        hovertemplate="신호: %{text}<br>날짜: %{x}<extra></extra>",
                        text=puddle_buys['Puddle']
                    ))

                    
            # (5) RSI 과매도 구간 (파란색 점 마커)
            if 'RSI' in df.columns:
                # 중요: RSI 컬럼을 숫자형으로 변환 (빈 문자열 등은 NaN 처리)
                temp_rsi = pd.to_numeric(df['RSI'], errors='coerce')
                
                # 숫자인 값들 중에서만 30 이하인 데이터 필터링
                oversold = df[temp_rsi <= 30]
                
                if not oversold.empty:
                    fig.add_trace(go.Scatter(
                        x=oversold['Date'], y=oversold['Close'],
                        mode='markers', name='RSI Oversold',
                        marker=dict(symbol='circle', size=8, color='#0066CC', opacity=0.7)
                    ))

            # 레이아웃 설정 (기존 차트 스타일 재현)
            fig.update_layout(
                height=750, 
                template='plotly_white', 
                xaxis_rangeslider_visible=False,
                yaxis_title="Price ($)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                margin=dict(l=10, r=10, t=50, b=10)
            )
            
            # 그리드 및 날짜 포맷 설정
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0')

            st.plotly_chart(fig, use_container_width=True)

            # --- 데이터 테이블 및 신호 안내 ---
            col_left, col_right = st.columns([2, 1])
            
            with col_left:
                st.subheader("📋 최근 분석 데이터 (15일)")
                cols = ['Date', 'Close', 'Change(%)', 'RSI', 'FG index', 'FG/RSI signal', 'Puddle']
                st.dataframe(df[[c for c in cols if c in df.columns]].tail(15).sort_values('Date', ascending=False), use_container_width=True)

            with col_right:
                st.subheader("🔔 현재 주요 신호")
                current_puddle = last_row.get('Puddle', '')
                current_vix = last_row.get('VIX1D>VIX', '')
                
                if current_puddle:
                    st.warning(f"⚠️ **Puddle 발견:** {current_puddle}")
                if current_vix == 'BUY':
                    st.error("🔥 **VIX 신호:** 변동성 기반 매수 적기!")
                
                st.info(f"💡 **RSI/FG 전략:** {last_row.get('FG/RSI signal', '관망')}")
                
                # CSV 다운로드
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📊 전체 분석 데이터 다운로드", csv, f"{selected_name}_full_data.csv", "text/csv")
        else:
            st.error("데이터를 불러오지 못했습니다. 티커나 네트워크 상태를 확인해주세요.")