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
    with st.spinner('차트와 신호를 선명하게 구성 중입니다...'):
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

            # --- 메인 차트 (시인성 강화 버전) ---
            st.subheader(f"📈 {selected_name} 주가 및 매매 전략 트렌드")
            
            fig = go.Figure()
            
            # (1) 주가 라인 (깔끔한 블랙 계열)
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Close'],
                mode='lines',
                name='Price',
                line=dict(color='#1A1A1B', width=2),
                connectgaps=True
            ))
            
            # (2) 이동평균선 (기존보다 더 얇게 처리하여 보조 역할 강조)
            ma_colors = {'MA20': '#3498DB', 'MA60': '#E67E22', 'MA120': '#E74C3C', 'MA200': '#9B59B6'}
            for ma, color in ma_colors.items():
                if ma in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df['Date'], y=df[ma], name=ma, 
                        line=dict(color=color, width=1.0), opacity=0.3
                    ))
            
            # (3) VIX1D > VIX Buy 신호 (선명한 수직 점선)
            if 'VIX1D>VIX' in df.columns:
                vix_buys = df[df['VIX1D>VIX'] == 'BUY']
                for v_date in vix_buys['Date']:
                    fig.add_vline(
                        x=v_date, 
                        line_width=1.5, 
                        line_dash="dash", 
                        line_color="#FF0000", # 강렬한 레드
                        opacity=0.6 # 선명도 상향
                    )

            # (4) Puddle 매수 신호 (진한 초록색 대형 삼각형)
            if 'Puddle' in df.columns:
                p_df = df[df['Puddle'].astype(str).str.len() > 1].copy()
                if not p_df.empty:
                    fig.add_trace(go.Scatter(
                        x=p_df['Date'], y=p_df['Low'] * 0.96, # 가독성을 위해 주가와 살짝 거리 유지
                        mode='markers', 
                        name='Puddle Buy (진입점)',
                        marker=dict(
                            symbol='triangle-up', 
                            size=15, # 크기 확대
                            color='#00FF00', 
                            line=dict(width=2, color='#006400') # 테두리 추가로 선명도 확보
                        ),
                        text=p_df['Puddle'],
                        hovertemplate="<b>매수신호: %{text}</b><br>날짜: %{x}<extra></extra>"
                    ))

            # (5) RSI 과매도 구간 (선명한 파란색 원형 마커)
            if 'RSI' in df.columns:
                temp_rsi = pd.to_numeric(df['RSI'], errors='coerce')
                oversold = df[temp_rsi <= 30]
                if not oversold.empty:
                    fig.add_trace(go.Scatter(
                        x=oversold['Date'], y=oversold['Close'],
                        mode='markers', 
                        name='RSI 과매도 (30이하)',
                        marker=dict(
                            symbol='circle', 
                            size=10, 
                            color='#007FFF', 
                            line=dict(width=1.5, color='#00008B') # 테두리 추가
                        ),
                        hovertemplate="<b>RSI 과매도</b><br>가격: %{y}<br>날짜: %{x}<extra></extra>"
                    ))

            # 레이아웃 최적화
            fig.update_layout(
                height=700, 
                template='plotly_white', 
                hovermode='x unified',
                xaxis_rangeslider_visible=False,
                yaxis_title="Stock Price ($)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                margin=dict(l=10, r=10, t=50, b=10)
            )
            
            # 격자 및 날짜 축 설정 강화
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0', nticks=20)
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0')

            st.plotly_chart(fig, use_container_width=True)

            # --- 데이터 섹션 ---
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.subheader("📋 최근 분석 데이터 (15일)")
                cols = ['Date', 'Close', 'Change(%)', 'RSI', 'FG index', 'FG/RSI signal', 'Puddle']
                st.dataframe(df[[c for c in cols if c in df.columns]].tail(15).sort_values('Date', ascending=False), use_container_width=True)

            with col_right:
                st.subheader("🔔 신호 및 전략")
                current_p = last_row.get('Puddle', '')
                if current_p: 
                    st.warning(f"⚠️ **신호 발생:** {current_p}")
                
                vix_stat = last_row.get('VIX1D>VIX', '')
                if vix_stat == 'BUY':
                    st.error("🔥 **VIX 매수 신호 포착!**")
                
                st.success(f"💡 **현재 권장 전략:** {last_row.get('FG/RSI signal', '관망')}")
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📊 전체 데이터 CSV", csv, f"{selected_name}_full.csv", "text/csv")
        else:
            st.error("데이터를 불러오지 못했습니다.")