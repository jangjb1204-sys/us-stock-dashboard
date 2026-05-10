import streamlit as st
import pandas as pd
import os
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="US Stock Analyzer", layout="wide")

st.title("🧠 US Stock Multi-Signal Analyzer")
st.caption("내 전략(Puddle, VIX1D>VIX, FG/RSI)이 반영된 차트")

st.sidebar.header("설정")

ticker_configs = {
    'SOXL': 'SOXL (3x 반도체)', '^GSPC': 'S&P 500', '^IXIC': 'NASDAQ',
    'SSO': 'SSO (2x S&P)', 'QLD': 'QLD (2x NASDAQ)', 'TSLA': 'TESLA',
    'GLD': 'Gold', 'SLV': 'Silver'
}

selected_tickers = st.sidebar.multiselect(
    "분석할 종목 선택", 
    options=list(ticker_configs.keys()),
    default=['SOXL', '^GSPC'],
    format_func=lambda x: ticker_configs[x]
)

if st.sidebar.button("🚀 데이터 새로 분석하기", type="primary"):
    with st.spinner("분석 및 파일 생성 중..."):
        try:
            from stock_analyzer import fetch_common_market_data, process_stock_data, get_ticker_configs
            common_data = fetch_common_market_data(period='4y')
            
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i, ticker in enumerate(selected_tickers):
                name = ticker_configs.get(ticker, ticker)
                status.write(f"🔄 {ticker} 분석 중... ({i+1}/{len(selected_tickers)})")
                process_stock_data(ticker, name, common_data, period='4y', delta=600)
                progress_bar.progress((i+1)/len(selected_tickers))
                time.sleep(0.5)
            
            st.success("✅ 분석 완료!")
            st.rerun()
        except Exception as e:
            st.error(f"오류: {e}")

# ===================== 결과 표시 =====================
st.header("📁 분석 결과")

folder = "data/US_stock"

if os.path.exists(folder):
    excel_files = [f for f in os.listdir(folder) if f.endswith("_table.xlsx")]
    
    if excel_files:
        names = sorted([f.replace("_table.xlsx", "") for f in excel_files])
        selected = st.selectbox("종목 선택", names)
        
        excel_path = os.path.join(folder, f"{selected}_table.xlsx")
        df = pd.read_excel(excel_path) if os.path.exists(excel_path) else pd.DataFrame()
        
        tab1, tab2, tab3 = st.tabs(["📊 테이블", "🖼️ 저장된 이미지", "📈 나의 전략 차트"])

        with tab1:
            st.subheader("전체 데이터 테이블")
            st.dataframe(df, use_container_width=True, height=600)

        with tab2:
            st.subheader("저장된 이미지")
            cols = st.columns(3)
            for idx, (title, filename) in enumerate([
                ("테이블 이미지", "_table.jpg"),
                ("캔들 차트", "_chart.jpg"),
                ("시그널 차트", "_with signals.png")
            ]):
                with cols[idx]:
                    st.write(f"**{title}**")
                    path = os.path.join(folder, f"{selected}{filename}")
                    if os.path.exists(path):
                        st.image(path)
                    else:
                        st.write("파일 없음")

        with tab3:
            st.subheader(f"{selected} - 나의 전략 차트")
            if not df.empty and 'Date' in df.columns and 'Close' in df.columns:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                    row_heights=[0.7, 0.3], vertical_spacing=0.05)

                # 가격 + MA + Puddle 신호
                fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name='Close', line=dict(width=2.5)), row=1, col=1)
                
                for ma in ['MA20', 'MA60', 'MA120', 'MA200']:
                    if ma in df.columns:
                        fig.add_trace(go.Scatter(x=df['Date'], y=df[ma], name=ma), row=1, col=1)

                # Puddle 신호 표시
                if 'Puddle' in df.columns:
                    puddle_signals = df[df['Puddle'].str.contains(r'[a-zA-Z]', na=False)]
                    if not puddle_signals.empty:
                        fig.add_trace(go.Scatter(
                            x=puddle_signals['Date'], 
                            y=puddle_signals['Close'] * 0.97,
                            mode='markers',
                            name='Puddle Signal',
                            marker=dict(symbol='triangle-up', size=14, color='red')
                        ), row=1, col=1)

                # VIX1D > VIX 신호
                if 'VIX1D>VIX' in df.columns:
                    vix_buy = df[df['VIX1D>VIX'] == 'BUY']
                    if not vix_buy.empty:
                        fig.add_trace(go.Scatter(
                            x=vix_buy['Date'], 
                            y=vix_buy['Close'] * 0.95,
                            mode='markers',
                            name='VIX1D>VIX BUY',
                            marker=dict(symbol='star', size=12, color='lime')
                        ), row=1, col=1)

                # RSI
                if 'RSI' in df.columns:
                    fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], name='RSI', line=dict(color='purple')), row=2, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)

                fig.update_layout(height=750, title=f"{selected} - 전략 종합 차트")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("차트 데이터가 없습니다.")
    else:
        st.info("아직 분석 파일이 없습니다.\n\n왼쪽에서 분석 버튼을 눌러주세요.")