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

# 3. 사이드바 설정 (요청하신 정확한 티커 리스트 반영)
with st.sidebar:
    st.header("🔍 분석 설정")
    ticker_list = {
        'SOXL': 'SOXL',
        '^GSPC': 'S&P500',
        '^IXIC': 'NASDAQ',
        'SSO': 'SSO',
        'QLD': 'QLD',
        'GLD': 'GOLD',
        'BTGD': 'BTGD',
        'SLV': 'SILVER',
        'KORU': 'KORU',
        'TSLA': 'TESLA'
    }
    selected_name = st.selectbox("분석할 종목 선택", list(ticker_list.values()))
    selected_ticker = [k for k, v in ticker_list.items() if v == selected_name][0]
    
    period = st.selectbox("데이터 조회 기간", ["1y", "2y", "4y", "5y"], index=1)
    process_btn = st.button("실시간 데이터 분석 시작")

# 4. 실행 로직
if process_btn:
    with st.spinner(f'{selected_name} 데이터를 분석 중입니다...'):
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

            # --- 메인 차트 (시인성 극대화 버전) ---
            st.subheader(f"📈 {selected_name} 주가 및 매매 전략")
            
            fig = go.Figure()
            
            # (1) 주가 라인
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Close'],
                mode='lines',
                name='Price',
                line=dict(color='#1A1A1B', width=2.5),
                connectgaps=True
            ))
            
            # (2) 이동평균선 (선명한 설정)
            ma_colors = {
                'MA20': '#2980B9', 'MA60': '#D35400', 
                'MA120': '#C0392B', 'MA200': '#8E44AD'
            }
            for ma, color in ma_colors.items():
                if ma in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df['Date'], y=df[ma], name=ma, 
                        line=dict(color=color, width=1.8),
                        opacity=0.7 
                    ))
            
            # (3) VIX1D > VIX Buy 신호 (강력한 빨간 실선)
            if 'VIX1D>VIX' in df.columns:
                vix_buys = df[df['VIX1D>VIX'] == 'BUY']
                for v_date in vix_buys['Date']:
                    fig.add_vline(
                        x=v_date, line_width=2, line_dash="solid", 
                        line_color="#FF0000", opacity=0.4 
                    )

            # (4) Puddle 매수 신호 (형광 초록 삼각형)
            if 'Puddle' in df.columns:
                p_df = df[df['Puddle'].astype(str).str.len() > 1].copy()
                if not p_df.empty:
                    fig.add_trace(go.Scatter(
                        x=p_df['Date'], y=p_df['Low'] * 0.95,
                        mode='markers', name='Puddle Signal',
                        marker=dict(
                            symbol='triangle-up', size=16, 
                            color='#00FF00', line=dict(width=2, color='#004d00')
                        ),
                        text=p_df['Puddle'],
                        hovertemplate="<b>%{text}</b><br>날짜: %{x}<extra></extra>"
                    ))

            # (5) RSI 과매도 구간 (선명한 블루 서클)
            if 'RSI' in df.columns:
                temp_rsi = pd.to_numeric(df['RSI'], errors='coerce')
                oversold = df[temp_rsi <= 30]
                if not oversold.empty:
                    fig.add_trace(go.Scatter(
                        x=oversold['Date'], y=oversold['Close'],
                        mode='markers', name='RSI Oversold',
                        marker=dict(
                            symbol='circle', size=10, 
                            color='#3498DB', line=dict(width=2, color='#1A5276')
                        ),
                        hovertemplate="<b>RSI 과매도</b><br>가격: %{y}<br>날짜: %{x}<extra></extra>"
                    ))

            # 레이아웃 설정
            fig.update_layout(
                height=700, template='plotly_white', hovermode='x unified',
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                margin=dict(l=10, r=10, t=50, b=10)
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # --- 하단 분석 섹션 ---
            col_l, col_r = st.columns([2, 1])
            with col_l:
                st.subheader("📋 분석 상세")
                cols = ['Date', 'Close', 'Change(%)', 'RSI', 'FG index', 'FG/RSI signal', 'Puddle']
                st.dataframe(df[[c for c in cols if c in df.columns]].tail(15).sort_values('Date', ascending=False), use_container_width=True)

            with col_r:
                st.subheader("🔔 신호 분석")
                if last_row.get('Puddle'):
                    st.warning(f"⚠️ **신호:** {last_row['Puddle']}")
                if last_row.get('VIX1D>VIX') == 'BUY':
                    st.error("🚨 **VIX 변동성 매수 신호!**")
                st.success(f"💡 **전략:** {last_row.get('FG/RSI signal', '관망')}")
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📊 데이터 CSV 다운로드", csv, f"{selected_name}.csv", "text/csv")
        else:
            st.error(f"{selected_name} 데이터를 가져오는 데 실패했습니다.")