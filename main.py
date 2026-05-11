import streamlit as st
import pandas as pd
from stock_analyzer import get_full_analysis, fetch_common_market_data
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="US Stock Insight", layout="wide")

@st.cache_data(ttl=3600)
def get_cached_common_data(period):
    return fetch_common_market_data(period)

st.title("🇺🇸 US Stock 분석 대시보드")

# 2. 사이드바 설정
with st.sidebar:
    st.header("🔍 분석 설정")
    ticker_list = {
        'SOXL': 'SOXL (반도체 3x)', '^GSPC': 'S&P500 (시장)', '^IXIC': 'NASDAQ (기술주)',
        'TSLA': 'TESLA (테슬라)', 'QLD': 'QLD (나스닥 2x)', 'NVDA': 'NVIDIA (엔비디아)',
        'TQQQ': 'TQQQ (나스닥 3x)', 'AAPL': 'APPLE (애플)'
    }
    selected_name = st.selectbox("종목 선택", list(ticker_list.values()))
    selected_ticker = [k for k, v in ticker_list.items() if v == selected_name][0]
    period = st.selectbox("조회 기간", ["1y", "2y", "4y", "5y"], index=1)
    process_btn = st.button("분석 시작")

# 3. 메인 로직
if process_btn:
    with st.spinner('차트를 깔끔하게 생성 중입니다...'):
        common_data = get_cached_common_data(period)
        df = get_full_analysis(selected_ticker, selected_name, common_data, period=period)
        
        if not df.empty:
            # 상단 지표
            last_row = df.iloc[-1]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("현재가", f"${last_row['Close']:.2f}", f"{last_row['Change(%)']}%")
            m2.metric("RSI (14)", last_row['RSI'])
            m3.metric("Fear & Greed", f"{last_row.get('fg_index', 'N/A')}")
            m4.metric("10Y Treasury", f"{last_row.get('10Y Treasury', 'N/A')}%")

            # --- 깔끔한 라인 차트 구성 ---
            st.subheader(f"📈 {selected_name} 주가 추이 및 주요 신호")
            
            fig = go.Figure()

            # (1) 주가 라인 (Area 스타일로 하단 채우기)
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Close'],
                mode='lines',
                name='Price',
                line=dict(color='#1f77b4', width=2),
                fill='tozeroy',
                fillcolor='rgba(31, 119, 180, 0.1)' # 아주 연한 파란색 배경
            ))

            # (2) 주요 이동평균선 (심플하게 20일과 200일만 표시하거나 연하게 처리)
            ma_list = {'MA20': 'rgba(255, 152, 0, 0.5)', 'MA200': 'rgba(156, 39, 176, 0.5)'}
            for ma, color in ma_list.items():
                if ma in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df['Date'], y=df[ma], name=ma,
                        line=dict(color=color, width=1.5, dash='dot')
                    ))

            # (3) VIX1D > VIX 신호 (배경 강조)
            if 'VIX1D>VIX' in df.columns:
                vix_buys = df[df['VIX1D>VIX'] == 'BUY']
                for v_date in vix_buys['Date']:
                    fig.add_vline(x=v_date, line_width=1, line_dash="dash", line_color="#FF4500", opacity=0.2)

            # (4) Puddle 매수 신호 (직관적인 마커)
            if 'Puddle' in df.columns:
                puddle_buys = df[df['Puddle'].astype(str).str.len() > 1]
                if not puddle_buys.empty:
                    fig.add_trace(go.Scatter(
                        x=puddle_buys['Date'], y=puddle_buys['Close'],
                        mode='markers', name='Buy Signal',
                        marker=dict(symbol='star', size=11, color='#FFD700', line=dict(width=1, color='black')),
                        text=puddle_buys['Puddle']
                    ))

            # (5) RSI 과매도 구간 (안전한 숫자 변환 후 표시)
            if 'RSI' in df.columns:
                temp_rsi = pd.to_numeric(df['RSI'], errors='coerce')
                oversold = df[temp_rsi <= 30]
                if not oversold.empty:
                    fig.add_trace(go.Scatter(
                        x=oversold['Date'], y=oversold['Close'],
                        mode='markers', name='Oversold',
                        marker=dict(symbol='circle', size=7, color='#0066CC', opacity=0.8)
                    ))

            # 레이아웃 최적화 (여백 줄이고 가독성 향상)
            fig.update_layout(
                height=600,
                margin=dict(l=20, r=20, t=30, b=20),
                template='plotly_white',
                hovermode='x unified', # 마우스 올리면 해당 날짜 모든 데이터 요약
                xaxis=dict(showgrid=False),
                yaxis=dict(position=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # 하단 정보
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("📋 상세 데이터")
                st.dataframe(df.tail(15).sort_values('Date', ascending=False), use_container_width=True)
            with c2:
                st.subheader("🔔 실시간 코멘트")
                if last_row.get('Puddle'): st.warning(f"🎯 Puddle 신호 포착: {last_row['Puddle']}")
                st.info(f"💰 현재 전략: {last_row.get('FG/RSI signal', '데이터 확인 중')}")

        else:
            st.error("데이터 분석 결과를 가져올 수 없습니다.")