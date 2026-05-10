import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="US Stock Analyzer", layout="wide")

st.title("🧠 US Stock Multi-Signal Analyzer")
st.caption("원래 생성되던 이미지와 엑셀 파일을 Streamlit에서 바로 확인")

# 사이드바
if st.sidebar.button("🚀 데이터 새로 분석하기", type="primary"):
    with st.spinner("분석 중... (최대 3~5분 걸릴 수 있습니다)"):
        try:
            from stock_analyzer import fetch_common_market_data, process_stock_data, get_ticker_configs
            
            common_data = fetch_common_market_data(period='4y')
            ticker_configs = get_ticker_configs()
            
            for ticker, name in ticker_configs.items():
                st.write(f"🔄 {ticker} ({name}) 분석 중...")
                process_stock_data(ticker, name, common_data, period='4y', delta=600)
            
            st.success("✅ 분석이 완료되었습니다! 아래에서 파일을 확인하세요.")
            st.rerun()   # 화면 새로고침
            
        except Exception as e:
            st.error(f"오류: {e}")

# ====================== 파일 보여주기 ======================
folder = "data/US_stock"

st.header("📁 생성된 파일 목록")

if os.path.exists(folder):
    excel_files = [f for f in os.listdir(folder) if f.endswith("_table.xlsx")]
    
    if excel_files:
        # 종목 이름 추출
        ticker_names = sorted(list(set(f.replace("_table.xlsx", "") for f in excel_files)))
        selected = st.selectbox("종목 선택", options=ticker_names)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📊 데이터 테이블")
            excel_path = os.path.join(folder, f"{selected}_table.xlsx")
            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path)
                st.dataframe(df, use_container_width=True)
        
        with col2:
            st.subheader("🖼️ 테이블 이미지")
            img_path = os.path.join(folder, f"{selected}_table.jpg")
            if os.path.exists(img_path):
                st.image(img_path)
            else:
                st.write("테이블 이미지가 없습니다.")
            
            st.subheader("📈 캔들 차트")
            chart_path = os.path.join(folder, f"{selected}_chart.jpg")
            if os.path.exists(chart_path):
                st.image(chart_path)
            
            st.subheader("📉 시그널 차트")
            signal_path = os.path.join(folder, f"{selected}_with signals.png")
            if os.path.exists(signal_path):
                st.image(signal_path)
    else:
        st.info("아직 분석된 파일이 없습니다.\n\n왼쪽 사이드바에서 **'데이터 새로 분석하기'** 버튼을 눌러주세요.")
else:
    st.warning("data/US_stock 폴더가 없습니다. 분석을 먼저 실행해주세요.")