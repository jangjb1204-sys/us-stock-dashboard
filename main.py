import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="US Stock Dashboard", layout="wide")

st.title("📈 US Stock Analysis Dashboard")

# 사이드바: 티커 입력
ticker_input = st.sidebar.text_input("Enter Ticker (e.g., AAPL, TSLA, NVDA)", "AAPL").upper()
period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)

if ticker_input:
    try:
        # 데이터 가져오기
        stock = yf.Ticker(ticker_input)
        hist = stock.history(period=period)
        info = stock.info

        if hist.empty:
            st.error("데이터를 불러올 수 없습니다. 티커를 확인해 주세요.")
        else:
            # 1. 상단 지표 요약 (Table 형태)
            st.subheader(f"📊 {ticker_input} Key Metrics")
            
            # 원본 지표 구성
            current_price = info.get('currentPrice', hist['Close'].iloc[-1])
            prev_close = info.get('previousClose', hist['Close'].iloc[-2])
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
            
            metrics_df = pd.DataFrame({
                "Metric": ["Current Price", "Change ($)", "Change (%)", "Market Cap", "P/E Ratio", "52 Week High", "52 Week Low"],
                "Value": [
                    f"${current_price:,.2f}",
                    f"{change:+,.2f}",
                    f"{change_pct:+.2f}%",
                    f"${info.get('marketCap', 0):,}",
                    f"{info.get('trailingPE', 'N/A')}",
                    f"${info.get('fiftyTwoWeekHigh', 0):,.2f}",
                    f"${info.get('fiftyTwoWeekLow', 0):,.2f}"
                ]
            })
            st.table(metrics_df)

            # 2. 주가 차트 (이전 Plot 유지)
            st.subheader("Price Action")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hist.index, 
                y=hist['Close'], 
                mode='lines', 
                name='Close Price',
                line=dict(color='#00FFCC', width=2)
            ))
            
            fig.update_layout(
                template="plotly_dark",
                xaxis_title="Date",
                yaxis_title="Price (USD)",
                margin=dict(l=20, r=20, t=20, b=20),
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

            # 3. 엑셀 다운로드 기능 (xlsxwriter 에러 해결 포인트)
            st.subheader("Download Data")
            output = BytesIO()
            # engine='xlsxwriter'를 사용하기 위해 패키지 설치가 선행되어야 함
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                hist.to_excel(writer, sheet_name='Stock_Data')
                # 시트 포맷팅 등을 추가할 수 있음
            
            excel_data = output.getvalue()
            st.download_button(
                label="📥 Download Historical Data as Excel",
                data=excel_data,
                file_name=f"{ticker_input}_history.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # 4. Raw Data 표시
            with st.expander("View Raw Historical Data"):
                st.dataframe(hist.sort_index(ascending=False), use_container_width=True)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")