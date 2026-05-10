import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="US Stock Analyzer", layout="wide")
st.title("🧠 US Stock Multi-Signal Analyzer")
st.caption("원래 생성되던 이미지와 엑셀 파일을 Streamlit에서 바로 확인")

ticker_configs = { ... }  # 기존과 동일

if st.sidebar.button("🚀 데이터 새로 분석하기", type="primary"):
    # 분석 실행 (기존 코드)
    ...

# ===================== 파일 기반 결과 보여주기 =====================
folder = "data/US_stock"

if os.path.exists(folder):
    st.header("📁 생성된 파일 목록")
    
    files = os.listdir(folder)
    tickers = set()
    
    for f in files:
        if f.endswith("_table.xlsx"):
            ticker_name = f.replace("_table.xlsx", "")
            tickers.add(ticker_name)
    
    selected = st.selectbox("종목 선택", sorted(list(tickers)))
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 테이블")
        excel_path = os.path.join(folder, f"{selected}_table.xlsx")
        if os.path.exists(excel_path):
            df = pd.read_excel(excel_path)
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
        
        signal_path = os.path.join(folder, f"{selected}_with signals.png")
        if os.path.exists(signal_path):
            st.image(signal_path)