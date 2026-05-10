import streamlit as st
import pandas as pd
import os
import time

st.set_page_config(page_title="US Stock Analyzer", layout="wide")

st.title("🧠 US Stock Multi-Signal Analyzer")
st.caption("종목별 테이블 · 이미지 · 차트 자동 생성 대시보드")

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
    with st.spinner("분석 시작..."):
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
            
            st.success("✅ 분석 및 파일 생성 완료!")
            st.rerun()
            
        except Exception as e:
            st.error(f"오류: {e}")

# ===================== 결과 표시 =====================
st.header("📁 생성된 분석 파일")

folder = "data/US_stock"

if os.path.exists(folder):
    excel_files = [f for f in os.listdir(folder) if f.endswith("_table.xlsx")]
    
    if excel_files:
        names = sorted([f.replace("_table.xlsx", "") for f in excel_files])
        selected = st.selectbox("종목 선택", names)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📊 테이블")
            if os.path.exists(os.path.join(folder, f"{selected}_table.xlsx")):
                df = pd.read_excel(os.path.join(folder, f"{selected}_table.xlsx"))
                st.dataframe(df, use_container_width=True)
        
        with col2:
            st.subheader("🖼️ 테이블 이미지")
            img_path = os.path.join(folder, f"{selected}_table.jpg")
            if os.path.exists(img_path):
                st.image(img_path)
            
            st.subheader("📈 차트")
            chart_path = os.path.join(folder, f"{selected}_chart.jpg")
            if os.path.exists(chart_path):
                st.image(chart_path)
    else:
        st.info("아직 생성된 파일이 없습니다.\n\n왼쪽 사이드바에서 분석 버튼을 눌러주세요.")
else:
    st.info("분석을 먼저 실행해주세요.")