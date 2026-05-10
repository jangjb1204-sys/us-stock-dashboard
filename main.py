import streamlit as st
import pandas as pd
import os
import time

st.set_page_config(page_title="US Stock Analyzer", page_icon="📈", layout="wide")

st.title("🧠 US Stock Multi-Signal Analyzer")
st.markdown("**Fear & Greed + RSI + Puddle + VIX 전략 대시보드**")

st.sidebar.header("설정")

ticker_configs = {
    'SOXL': 'SOXL (3x 반도체)', 
    '^GSPC': 'S&P 500', 
    '^IXIC': 'NASDAQ',
    'SSO': 'SSO (2x S&P)', 
    'QLD': 'QLD (2x NASDAQ)', 
    'TSLA': 'TESLA',
    'GLD': 'Gold', 
    'SLV': 'Silver'
}

selected_tickers = st.sidebar.multiselect(
    "분석할 종목 선택", 
    options=list(ticker_configs.keys()),
    default=['SOXL', '^GSPC', 'TSLA'],
    format_func=lambda x: ticker_configs[x]
)

if st.sidebar.button("🚀 데이터 새로 분석하기", type="primary"):
    with st.spinner("분석 중입니다... (1~3분 소요)"):
        try:
            from stock_analyzer import fetch_common_market_data, process_stock_data
            
            common_data = fetch_common_market_data(period='4y')
            
            progress = st.progress(0)
            for i, ticker in enumerate(selected_tickers):
                name = ticker_configs.get(ticker, ticker)
                st.write(f"🔄 {ticker} 분석 중...")
                process_stock_data(ticker, name, common_data, period='4y', delta=600)
                progress.progress((i + 1) / len(selected_tickers))
                time.sleep(2)
            
            st.success("✅ 모든 분석이 완료되었습니다!")
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")

tab1, tab2, tab3 = st.tabs(["📋 Overview", "🔍 종목 상세", "🌍 시장 지표"])

with tab1:
    st.header("최근 분석 결과")
    folder = "data/US_stock"
    if os.path.exists(folder):
        files = [f for f in os.listdir(folder) if f.endswith("_table.xlsx")]
        if files:
            for f in files:
                name = f.replace("_table.xlsx", "")
                st.subheader(name)
                try:
                    df = pd.read_excel(os.path.join(folder, f))
                    st.dataframe(df.tail(10), use_container_width=True)
                except:
                    st.write("파일 읽기 실패")
        else:
            st.info("분석된 파일이 없습니다.")
    else:
        st.info("아직 분석된 데이터가 없습니다. 분석 버튼을 눌러주세요.")