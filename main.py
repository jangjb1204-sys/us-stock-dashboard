import streamlit as st
import pandas as pd
import numpy as np
from stock_analyzer import get_full_analysis, fetch_common_market_data
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="US Stock Expert Dashboard", layout="wide")

@st.cache_data(ttl=3600)
def get_cached_common_data(period):
    return fetch_common_market_data(period)

st.title("📊 US Stock 전문 분석 대시보드")

with st.sidebar:
    ticker_configs = {
        'SOXL': 'SOXL', '^GSPC': 'S&P500', '^IXIC': 'NASDAQ',
        'SSO': 'SSO', 'QLD': 'QLD', 'GLD': 'GOLD', 'TSLA': 'TESLA'
    }
    selected_name = st.selectbox("종목 선택", list(ticker_configs.values()))
    selected_ticker = [k for k, v in ticker_configs.items() if v == selected_name][0]
    period = st.selectbox("데이터 기간", ["1y", "2y", "4y", "5y"], index=2)
    process_btn = st.button("실시간 정밀 분석 실행")

if process_btn:
    with st.spinner('모든 기술적 지표 계산 중...'):
        common_data = get_cached_common_data(period)
        df = get_full_analysis(selected_ticker, common_data, period=period)
        
        if not df.empty:
            last = df.iloc[-1]
            # 1. 주요 지표 카드
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("현재가", f"${last['Close']:.2f}", f"{last['Change(%)']}%")
            c2.metric("RSI (14)", f"{last['RSI']}")
            c3.metric("F&G Index", f"{int(last.get('FG index', 0))}", last.get('rating', 'N/A'))
            c4.metric("Stochastic K/D", f"{last['Slow_K']}/{last['Slow_D']}")
            c5.metric("2-Sigma", f"±{last['2sigma(%)']}%")

            # 2. 인터랙티브 차트 (주가 + 이평선 + 모든 신호)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name='Price', line=dict(color='black', width=2)))
            
            # MA 라인
            for ma, color in {'MA20': '#2196F3', 'MA60': '#FF9800', 'MA120': '#F44336', 'MA200': '#9C27B0'}.items():
                fig.add_trace(go.Scatter(x=df['Date'], y=df[ma], name=ma, line=dict(width=1.2), opacity=0.6))

            # Puddle 신호 표시 (빨간 화살표)
            puddle_df = df[df['Puddle'] != ''].copy()
            fig.add_trace(go.Scatter(x=puddle_df['Date'], y=puddle_df['Low']*0.97, mode='markers', 
                                     name='Puddle Buy', marker=dict(symbol='triangle-up', size=12, color='red')))

            # SKEW 특이점 (노란색 원)
            if 'SKEW' in df.columns:
                skew_low = df[df['SKEW'] <= 127]
                fig.add_trace(go.Scatter(x=skew_low['Date'], y=skew_low['Close'], mode='markers', 
                                         name='Skew Low', marker=dict(symbol='circle', size=8, color='gold')))

            fig.update_layout(height=600, template='plotly_white', hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

            # 3. 데이터 테이블 (2-sigma 조건부 강조 재현)
            st.subheader("📋 정밀 분석 리스트 (최근 20일)")
            
            def highlight_sigma(row):
                style = [''] * len(row)
                try:
                    if float(row['Change(%)']) < -float(row['2sigma(%)']):
                        return ['background-color: #FFFF99'] * len(row)
                except: pass
                return style

            display_cols = ['Date', 'Close', 'Change(%)', '2sigma(%)', 'RSI', 'Slow_K', 'FG index', 'FG/RSI signal', 'Puddle', 'VIX1D>VIX', 'SKEW']
            recent_df = df[display_cols].tail(20).copy()
            recent_df['Date'] = recent_df['Date'].dt.strftime('%Y-%m-%d')
            
            st.dataframe(recent_df.sort_values('Date', ascending=False).style.apply(highlight_sigma, axis=1), use_container_width=True)

            # 4. 엑셀 다운로드 (원본 openpyxl 로직 대체)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Analysis')
            st.download_button(label="📥 전체 분석 결과 엑셀 다운로드", data=output.getvalue(), 
                               file_name=f"{selected_name}_analysis_{datetime.now().strftime('%y%m%d')}.xlsx")