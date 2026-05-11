import streamlit as st
import pandas as pd
from stock_analyzer import get_full_analysis, fetch_common_market_data
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="US Stock Insight Dashboard", layout="wide")

# 2. 데이터 캐싱
@st.cache_data(ttl=3600)
def get_cached_common_data(period):
    return fetch_common_market_data(period)

st.title("🇺🇸 US Stock 분석 대시보드")

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
    with st.spinner('차트를 생성 중입니다...'):
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

            # --- 메인 차트 (라인 차트로 변경) ---
            st.subheader(f"📈 {selected_name} 주가 추이 및 신호")
            
            fig = go.Figure()
            
            # (1) 주가 라인 (캔들 대신 종가 기준 단순 라인)
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Close'],
                mode='lines',
                name='Price',
                line=dict(color='#2C3E50', width=2), # 깔끔한 다크 그레이/네이비 톤
                connectgaps=True
            ))
            
            # (2) 이동평균선
            ma_colors = {'MA20': '#3498DB', 'MA60': '#E67E22', 'MA120': '#E74C3C', 'MA200': '#9B59B6'}
            for ma, color in ma_colors.items():
                if ma in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df['Date'], y=df[ma], name=ma, 
                        line=dict(color=color, width=1.2, dash='solid'), opacity=0.4
                    ))
            
            # (3) VIX1D > VIX Buy 신호 (배경 수직선)
            if 'VIX1D>VIX' in df.columns:
                vix_buys = df[df['VIX1D>VIX'] == 'BUY']
                for v_date in vix_buys['Date']:
                    fig.add_vline(x=v_date, line_width=1, line_dash="dot", line_color="#E74C3C", opacity=0.2)

            # (4) Puddle 매수 신호 (초록색 삼각형 마커)
            if 'Puddle' in df.columns:
                p_df = df[df['Puddle'].astype(str).str.len() > 1].copy()
                if not p_df.empty:
                    fig.add_trace(go.Scatter(
                        x=p_df['Date'], y=p_df['Low'] * 0.97,
                        mode='markers', name='Puddle Buy',
                        marker=dict(symbol='triangle-up', size=12, color='#27AE60'),
                        text=p_df['Puddle'],
                        hovertemplate="신호: %{text}<br>날짜: %{x}<extra></extra>"
                    ))

            # (5) RSI 과매도 구간 (파란색 점 마커)
            if 'RSI' in df.columns:
                temp_rsi = pd.to_numeric(df['RSI'], errors='coerce')
                oversold = df[temp_rsi <= 30]
                if not oversold.empty:
                    fig.add_trace(go.Scatter(
                        x=oversold['Date'], y=oversold['Close'],
                        mode='markers', name='RSI Oversold',
                        marker=dict(symbol='circle', size=7, color='#2980B9', opacity=0.8),
                        hovertemplate="RSI 과매도<br>가격: %{y}<br>날짜: %{x}<extra></extra>"
                    ))

            # 레이아웃 최적화
            fig.update_layout(
                height=650, 
                template='plotly_white', 
                hovermode='x unified', # 마우스 올렸을 때 날짜별로 모든 데이터 한눈에
                xaxis_rangeslider_visible=False,
                yaxis_title="Price ($)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                margin=dict(l=10, r=10, t=50, b=10)
            )
            
            # X/Y축 그리드 정리
            fig.update_xaxes(showgrid=True, gridcolor='#F2F3F4')
            fig.update_yaxes(showgrid=True, gridcolor='#F2F3F4')

            st.plotly_chart(fig, use_container_width=True)

            # --- 데이터 섹션 ---
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.subheader("📋 최근 분석 데이터 (15일)")
                cols = ['Date', 'Close', 'Change(%)', 'RSI', 'FG index', 'FG/RSI signal', 'Puddle']
                st.dataframe(df[[c for c in cols if c in df.columns]].tail(15).sort_values('Date', ascending=False), use_container_width=True)

            with col_right:
                st.subheader("🔔 실시간 신호 요약")
                current_p = last_row.get('Puddle', '')
                if current_p: st.warning(f"⚠️ **Puddle:** {current_p}")
                
                st.info(f"💡 **RSI/FG 전략:** {last_row.get('FG/RSI signal', '관망')}")
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📊 CSV 데이터 다운로드", csv, f"{selected_name}_data.csv", "text/csv")
        else:
            st.error("데이터 분석 실패. 티커를 확인해 주세요.")