import streamlit as st
import pandas as pd
import os
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="US Stock Analyzer", layout="wide")

st.title("🧠 US Stock Multi-Signal Analyzer")
st.caption("파일 저장 + Streamlit 직접 차트 표시")

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
                status.write(f"🔄 {ticker} ({name}) 분석 중... ({i+1}/{len(selected_tickers)})")
                process_stock_data(ticker, name, common_data, period='4y', delta=600)
                progress_bar.progress((i+1)/len(selected_tickers))
                time.sleep(0.5)
            
            st.success("✅ 분석 완료!")
            st.rerun()
            
        except Exception as e:
            st.error(f"오류: {e}")

# ====================== 결과 표시 ======================
st.header("📁 분석 결과")

folder = "data/US_stock"

if os.path.exists(folder):
    excel_files = [f for f in os.listdir(folder) if f.endswith("_table.xlsx")]
    
    if excel_files:
        names = sorted([f.replace("_table.xlsx", "") for f in excel_files])
        selected = st.selectbox("종목 선택", names)
        
        # ==================== 데이터 로드 ====================
        excel_path = os.path.join(folder, f"{selected}_table.xlsx")
        df = pd.read_excel(excel_path) if os.path.exists(excel_path) else pd.DataFrame()
        
        tab1, tab2, tab3 = st.tabs(["📊 테이블", "🖼️ 저장된 이미지", "📈 Streamlit 차트"])

        with tab1:
            st.subheader("데이터 테이블")
            if not df.empty:
                st.dataframe(df, use_container_width=True, height=600)
            else:
                st.write("테이블 데이터가 없습니다.")

        with tab2:
            st.subheader("저장된 이미지들")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**테이블 이미지**")
                img_path = os.path.join(folder, f"{selected}_table.jpg")
                if os.path.exists(img_path):
                    st.image(img_path)
                else:
                    st.write("테이블 이미지가 없습니다.")
            
            with col2:
                st.write("**캔들/가격 차트**")
                chart_path = os.path.join(folder, f"{selected}_chart.jpg")
                if os.path.exists(chart_path):
                    st.image(chart_path)
                else:
                    st.write("차트 이미지가 없습니다.")
            
            st.write("**시그널 차트**")
            signal_path = os.path.join(folder, f"{selected}_with signals.png")
            if os.path.exists(signal_path):
                st.image(signal_path)
            else:
                st.write("시그널 차트 이미지가 없습니다.")

        with tab3:
            st.subheader("Streamlit 실시간 차트")
            if not df.empty and 'Date' in df.columns and 'Close' in df.columns:
                # 가격 + MA 차트
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name='Close', line=dict(width=2.5)))
                for ma in ['MA20', 'MA60', 'MA120', 'MA200']:
                    if ma in df.columns:
                        fig1.add_trace(go.Scatter(x=df['Date'], y=df[ma], name=ma))
                fig1.update_layout(title=f"{selected} 가격 및 이동평균", height=500)
                st.plotly_chart(fig1, use_container_width=True)

                # RSI 차트
                if 'RSI' in df.columns:
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], name='RSI', line=dict(color='purple')))
                    fig2.add_hline(y=30, line_dash="dash", line_color="green")
                    fig2.add_hline(y=70, line_dash="dash", line_color="red")
                    fig2.update_layout(title="RSI", height=350)
                    st.plotly_chart(fig2, use_container_width=True)
            else:
                st.write("차트를 그릴 데이터가 없습니다.")
    else:
        st.info("아직 분석된 파일이 없습니다.\n\n왼쪽 사이드바에서 **데이터 새로 분석하기** 버튼을 눌러주세요.")
else:
    st.info("분석을 먼저 실행해주세요.")