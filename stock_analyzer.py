{\rtf1\ansi\ansicpg949\cocoartf2868
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww33400\viewh19040\viewkind0
\hyphauto1\hyphfactor90
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import pandas as pd\
pd.set_option('future.no_silent_downcasting', True)\
import yfinance as yf\
from datetime import datetime, timedelta\
import requests\
import json\
import numpy as np\
import matplotlib.pyplot as plt\
import plotly.graph_objects as go\
from plotly.subplots import make_subplots\
from openpyxl import Workbook\
from openpyxl.styles import PatternFill, Font\
from openpyxl.utils import get_column_letter\
import time\
import os\
\
# \uc0\u54260 \u45908  \u49373 \u49457 \
current_dir = os.getcwd()\
folder_name = "data/US_stock"\
folder_path = os.path.join(current_dir, folder_name)\
os.makedirs(folder_path, exist_ok=True)\
\
# \uc0\u49345 \u49688  \u51221 \u51032 \
SEARCH_DAYS = 365 * 4\
DATE_FORMAT = '%Y-%m-%d'\
COLORS = \{\
    'GREEN': '#008000', 'RED': '#FF0000', 'BLACK': '#000000',\
    'YELLOW_FILL': '#FFFF99', 'HEADER_FILL': '#D3D3D3', 'LATEST_FILL': '#E6E6FA',\
\}\
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'\
\
def fetch_fear_and_greed_index(start_date: str):\
    time.sleep(1)\
    url = f'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/\{start_date\}'\
    headers = \{'User-Agent': USER_AGENT\}\
    try:\
        response = requests.get(url, headers=headers, timeout=10)\
        data = json.loads(response.text)\
        data_list = data['fear_and_greed_historical']['data']\
        df = pd.DataFrame([\
            \{\
                'Date': datetime.fromtimestamp(item['x'] / 1000).strftime(DATE_FORMAT),\
                'FG index': round(item['y']),\
                'rating': item.get('rating', 'N/A')\
            \}\
            for item in data_list\
        ])\
        df['Date'] = pd.to_datetime(df['Date'])\
        df = df.sort_values('Date').drop_duplicates('Date', keep='first')\
        return df\
    except:\
        return None\
\
def fetch_common_market_data(period: str = '4y'):\
    print("\uc0\u44277 \u53685  \u49884 \u51109  \u51648 \u54364  \u49688 \u51665  \u51473 ...")\
    # (\uc0\u50668 \u44592 \u49436 \u48512 \u53552  \u44592 \u51316  \u53076 \u46300 \u51032  fetch_common_market_data \u54632 \u49688  \u45236 \u50857  \u44536 \u45824 \u47196  \u48373 \u49324 )\
    # \uc0\u45320 \u47924  \u44600 \u50612 \u49436  \u49373 \u47029 \u54664 \u51648 \u47564 , \u45817 \u49888 \u51060  \u50896 \u47000  \u44032 \u51652  \u52395  \u48264 \u51704  \u53076 \u46300  \u51204 \u52404 \u47484  \u45347 \u51004 \u49464 \u50836 .\
    # \uc0\u50500 \u47000 \u45716  \u54645 \u49900 \u47564  \u44036 \u45800 \u55176  \u45224 \u44596  \u48260 \u51204 \u51077 \u45768 \u45796 . \u50896 \u48376  \u53076 \u46300 \u47484  \u44536 \u45824 \u47196  \u49324 \u50857 \u54616 \u49464 \u50836 .\
\
    # ... (\uc0\u44592 \u51316  fetch_common_market_data, fetch_stock_data, calculate_rsi \u46321  \u47784 \u46304  \u54632 \u49688 \u47484  \u44536 \u45824 \u47196  \u48373 \u49324 )\
    \
    # \uc0\u47560 \u51648 \u47561 \u50640  return \u54616 \u45716  \u48512 \u48516 \u44620 \u51648  \u54252 \u54632 \
    return \{\
        'treasury': treasury,\
        'vix': vix,\
        'vix1d': vix1d,\
        'skew': skew,\
        'fg_data': fg_data\
    \}\
\
# \uc0\u8251  \u51473 \u50836 : \u45817 \u49888 \u51060  \u52376 \u51020 \u50640  \u51456  \u53076 \u46300  \u51473  \u52395  \u48264 \u51704  \u53360  \u48660 \u47197 (\u51204 \u52404 )\u51012  \
# stock_analyzer.py\uc0\u50640  \u44536 \u45824 \u47196  \u48373 \u49324 \u54644 \u49436  \u45347 \u51004 \u49464 \u50836 .\
# (import \uc0\u48512 \u48516  ~ if __name__ == "__main__": \u48512 \u48516 \u44620 \u51648 )\
\
def get_ticker_configs():\
    return \{\
        'SOXL': 'SOXL', '^GSPC': 'S&P500', '^IXIC': 'NASDAQ',\
        'SSO': 'SSO', 'QLD': 'QLD', 'TSLA': 'TESLA',\
        'GLD': 'GOLD', 'SLV': 'SILVER'\
    \}}