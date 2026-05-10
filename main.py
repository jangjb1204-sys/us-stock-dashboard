import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

st.set_page_config(page_title="US Stock Analyzer", layout="wide")

st.title("🧠 US Stock Multi-Signal Analyzer")
st.caption("원래 생성되던 이미지와 엑셀 파일을 Streamlit에서 바로 확인")

# 사이드바 설정
st.sidebar.header("⚙️ 설정")

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

# ====================== 분석 버튼 ======================
if st.sidebar.button("🚀 데이터 새로 분석하기", type="primary"):
    if not selected_tickers:
        st.warning("분석할 종목을至少 1개 이상 선택해주세요.")
    else:
        with st.spinner("분석을 시작합니다..."):
            try:
                from stock_analyzer import fetch_common_market_data, process_stock_data, get_ticker_configs
                
                start_time = time.time()
                common_data = fetch_common_market_data(period='4y')
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                time_text = st.empty()
                
                total = len(selected_tickers)
                results = {}
                
                for i, ticker in enumerate(selected_tickers):
                    name = ticker_configs.get(ticker, ticker)
                    
                    # 진행 상황 업데이트
                    progress = (i) / total
                    progress_bar.progress(progress)
                    
                    elapsed = time.time() - start_time
                    avg_time_per_stock = elapsed / (i + 1) if i > 0 else 30  # 초기 추정 30초
                    remaining = avg_time_per_stock * (total - i - 1)
                    
                    status_text.write(f"🔄 **{ticker} ({name})** 분석 중... ({i+1}/{total})")
                    time_text.write(f"⏱️ 경과 시간: **{elapsed/60:.1f}분** | 예상 남은 시간: **{remaining/60:.1f}분**")
                    
                    # 실제 분석 실행
                    df = process_stock_data(ticker, name, common_data, period='4y', delta=600)
                    results[ticker] = df
                    
                    time.sleep(0.5)  # UI 업데이트를 위한 약간의 딜레이
                
                # 완료
                progress_bar.progress(1.0)
                total_time = (time.time() - start_time) / 60
                st.success(f"🎉 모든 분석 완료! (총 소요시간: {total_time:.1f}분)")
                st.session_state['results'] = results
                st.rerun()
                
            except Exception as e:
                st.error(f"오류 발생: {e}")

# ====================== 결과 표시 ======================
st.header("📁 분석 결과")

folder = "data/US_stock"

if os.path.exists(folder):
    excel_files = [f for f in os.listdir(folder) if f.endswith("_table.xlsx")]
    
    if excel_files:
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
            
            st.subheader("📈 캔들 차트")
            chart_path = os.path.join(folder, f"{selected}_chart.jpg")
            if os.path.exists(chart_path):
                st.image(chart_path)
            
            st.subheader("📉 시그널 차트")
            signal_path = os.path.join(folder, f"{selected}_with signals.png")
            if os.path.exists(signal_path):
                st.image(signal_path)
    else:
        st.info("아직 분석된 파일이 없습니다.\n\n왼쪽에서 **데이터 새로 분석하기** 버튼을 눌러주세요.")
else:
    st.info("분석을 먼저 실행해주세요.")