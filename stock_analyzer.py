import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import yfinance as yf
from datetime import datetime, timedelta
import requests
import json
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter
import time
import os

# 폴더 생성
current_dir = os.getcwd()
folder_name = "data/US_stock"
folder_path = os.path.join(current_dir, folder_name)
os.makedirs(folder_path, exist_ok=True)

# 상수 정의
SEARCH_DAYS = 365 * 4
DATE_FORMAT = '%Y-%m-%d'
COLORS = {
    'GREEN': '#008000', 'RED': '#FF0000', 'BLACK': '#000000',
    'YELLOW_FILL': '#FFFF99', 'HEADER_FILL': '#D3D3D3', 'LATEST_FILL': '#E6E6FA',
}
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def fetch_fear_and_greed_index(start_date: str):
    time.sleep(1)
    url = f'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start_date}'
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        data = json.loads(response.text)
        data_list = data['fear_and_greed_historical']['data']
        df = pd.DataFrame([
            {
                'Date': datetime.fromtimestamp(item['x'] / 1000).strftime(DATE_FORMAT),
                'FG index': round(item['y']),
                'rating': item.get('rating', 'N/A')
            }
            for item in data_list
        ])
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').drop_duplicates('Date', keep='first')
        return df
    except:
        return None

def fetch_common_market_data(period: str = '4y'):
    print("공통 시장 지표 수집 중...")
    # 10년물 국채
    try:
        treasury = yf.Ticker('^TNX').history(period=period)[['Close']].rename(columns={'Close': '10Y Treasury'})
        treasury = treasury.reset_index()
        treasury['Date'] = pd.to_datetime(treasury['Date'].dt.date)
        treasury['10Y Treasury'] = treasury['10Y Treasury'].round(2)
        time.sleep(1)
    except:
        treasury = pd.DataFrame()

    # VIX
    try:
        vix = yf.Ticker('^VIX').history(period=period)[['Close']].rename(columns={'Close': 'VIX'})
        vix = vix.reset_index()
        vix['Date'] = pd.to_datetime(vix['Date'].dt.date)
        vix['VIX'] = vix['VIX'].round(1)
        time.sleep(1)
    except:
        vix = pd.DataFrame()

    # VIX1D
    try:
        vix1d = yf.Ticker('^VIX1D').history(period=period)[['Close']].rename(columns={'Close': 'VIX1D'})
        vix1d = vix1d.reset_index()
        vix1d['Date'] = pd.to_datetime(vix1d['Date'].dt.date)
        vix1d['VIX1D'] = vix1d['VIX1D'].round(1)
        time.sleep(1)
    except:
        vix1d = pd.DataFrame()

    # Fear and Greed
    start_date = (datetime.now() - timedelta(days=SEARCH_DAYS)).strftime(DATE_FORMAT)
    fg_data = fetch_fear_and_greed_index(start_date)

    return {
        'treasury': treasury,
        'vix': vix,
        'vix1d': vix1d,
        'fg_data': fg_data
    }

# 나머지 함수들은 당신이 원래 가진 코드를 그대로 사용하세요.
# (calculate_rsi, process_stock_data 등 모든 함수를 stock_analyzer.py에 넣어야 합니다)

# ... (여기에 당신이 원래 가진 stock_analyzer.py의 나머지 모든 함수를 붙여넣으세요)

def get_ticker_configs():
    return {
        'SOXL': 'SOXL', '^GSPC': 'S&P500', '^IXIC': 'NASDAQ',
        'SSO': 'SSO', 'QLD': 'QLD', 'TSLA': 'TESLA',
        'GLD': 'GOLD', 'SLV': 'SILVER'
    }