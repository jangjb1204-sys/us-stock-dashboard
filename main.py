{\rtf1\ansi\ansicpg949\cocoartf2868
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\hyphauto1\hyphfactor90
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import pandas as pd\
import os\
from datetime import datetime\
import time\
\
st.set_page_config(page_title="US Stock Analyzer", page_icon="\uc0\u55357 \u56520 ", layout="wide")\
\
st.title("\uc0\u55358 \u56800  US Stock Multi-Signal Analyzer")\
st.markdown("**Fear & Greed + RSI + Puddle + VIX \uc0\u51204 \u47029  \u45824 \u49884 \u48372 \u46300 **")\
\
st.sidebar.header("\uc0\u49444 \u51221 ")\
\
ticker_configs = \{\
    'SOXL': 'SOXL (3x \uc0\u48152 \u46020 \u52404 )', '^GSPC': 'S&P 500', '^IXIC': 'NASDAQ',\
    'SSO': 'SSO (2x S&P)', 'QLD': 'QLD (2x NASDAQ)', 'TSLA': 'TESLA',\
    'GLD': 'Gold', 'SLV': 'Silver'\
\}\
\
selected_tickers = st.sidebar.multiselect(\
    "\uc0\u48516 \u49437 \u54624  \u51333 \u47785  \u49440 \u53469 ", \
    options=list(ticker_configs.keys()),\
    default=['SOXL', '^GSPC', 'TSLA'],\
    format_func=lambda x: ticker_configs[x]\
)\
\
if st.sidebar.button("\uc0\u55357 \u56960  \u45936 \u51060 \u53552  \u49352 \u47196  \u48516 \u49437 \u54616 \u44592 ", type="primary"):\
    with st.spinner("\uc0\u48516 \u49437  \u51473 \u51077 \u45768 \u45796 ... \u51104 \u49884 \u47564  \u44592 \u45796 \u47140 \u51452 \u49464 \u50836  (1~3\u48516  \u49548 \u50836 )"):\
        try:\
            from stock_analyzer import fetch_common_market_data, process_stock_data, get_ticker_configs\
            \
            common_data = fetch_common_market_data(period='4y')\
            \
            for ticker in selected_tickers:\
                name = ticker_configs.get(ticker, ticker)\
                st.write(f"\uc0\u55357 \u56580  \{ticker\} \u48516 \u49437  \u51473 ...")\
                process_stock_data(ticker, name, common_data, period='4y', delta=600)\
                time.sleep(2)\
            \
            st.success("\uc0\u9989  \u47784 \u46304  \u48516 \u49437 \u51060  \u50756 \u47308 \u46104 \u50632 \u49845 \u45768 \u45796 !")\
            \
        except Exception as e:\
            st.error(f"\uc0\u50724 \u47448 \u44032  \u48156 \u49373 \u54664 \u49845 \u45768 \u45796 : \{e\}")\
\
# \uc0\u53485 \
tab1, tab2, tab3 = st.tabs(["\uc0\u55357 \u56523  Overview", "\u55357 \u56589  \u51333 \u47785  \u49345 \u49464 ", "\u55356 \u57101  \u49884 \u51109  \u51648 \u54364 "])\
\
with tab1:\
    st.header("\uc0\u52572 \u44540  \u48516 \u49437  \u44208 \u44284 ")\
    folder = "data/US_stock"\
    if os.path.exists(folder):\
        files = [f for f in os.listdir(folder) if f.endswith("_table.xlsx")]\
        for f in files:\
            name = f.replace("_table.xlsx", "")\
            st.subheader(name)\
            df = pd.read_excel(os.path.join(folder, f))\
            st.dataframe(df.tail(10), use_container_width=True)\
    else:\
        st.info("\uc0\u50500 \u51649  \u48516 \u49437 \u46108  \u45936 \u51060 \u53552 \u44032  \u50630 \u49845 \u45768 \u45796 . \u50812 \u51901 \u50640 \u49436  \u48516 \u49437  \u48260 \u53948 \u51012  \u45580 \u47084 \u51452 \u49464 \u50836 .")\
\
with tab2:\
    st.header("\uc0\u51333 \u47785  \u49345 \u49464  \u48372 \u44592 ")\
    ticker_choice = st.selectbox("\uc0\u51333 \u47785  \u49440 \u53469 ", selected_tickers)\
    name = ticker_configs.get(ticker_choice, ticker_choice)\
    file_path = f"data/US_stock/\{name\}_table.xlsx"\
    \
    if os.path.exists(file_path):\
        df = pd.read_excel(file_path)\
        st.dataframe(df, use_container_width=True)\
        \
        chart_path = f"data/US_stock/\{name\}_chart.jpg"\
        if os.path.exists(chart_path):\
            st.image(chart_path)\
    else:\
        st.warning("\uc0\u48516 \u49437 \u46108  \u54028 \u51068 \u51060  \u50630 \u49845 \u45768 \u45796 . \u47676 \u51200  \u48516 \u49437 \u51012  \u49892 \u54665 \u54644 \u51452 \u49464 \u50836 .")\
\
with tab3:\
    st.header("\uc0\u49884 \u51109  \u51204 \u52404  \u51648 \u54364 ")\
    st.write("\uc0\u44277 \u53685  \u51648 \u54364 \u45716  \u48516 \u49437  \u49892 \u54665  \u54980  \u54869 \u51064  \u44032 \u45733 \u54633 \u45768 \u45796 .")}