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

def fetch_stock_data(ticker: str, period: str):
    time.sleep(2)
    stock = yf.Ticker(ticker)
    data = stock.history(period=period).reset_index()
    if not data.empty:
        data['Date'] = pd.to_datetime(data['Date'].dt.date)
    return data

def calculate_rsi(data: pd.DataFrame, window: int = 14):
    if len(data) < window:
        return pd.Series([np.nan] * len(data), index=data.index)
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).round(2)

def calculate_moving_averages(data: pd.DataFrame):
    for window in [20, 60, 120, 200]:
        if len(data) >= window:
            data[f'MA{window}'] = data['Close'].rolling(window=window).mean().round(2)
    return data

def generate_fg_rsi_signals(data: pd.DataFrame):
    def apply_rules(row):
        if pd.isna(row.get('RSI')):
            return '1x BUY'
        rsi = row['RSI']
        fg_idx = row.get('FG index', -1)
        if rsi >= 60 or (not pd.isna(fg_idx) and 51 <= fg_idx <= 100):
            return 'BUY STOP'
        elif rsi <= 30 or (not pd.isna(fg_idx) and 26 <= fg_idx <= 50):
            return '2x BUY'
        elif rsi <= 20 or (not pd.isna(fg_idx) and 0 <= fg_idx <= 25):
            return '3x BUY'
        return '1x BUY'
    
    data['FG/RSI signal'] = data.apply(apply_rules, axis=1)
    return data

def process_stock_data(ticker: str, name: str, common_data: dict, period: str = '4y', delta: int = 600):
    data = fetch_stock_data(ticker, period)
    if data.empty:
        return pd.DataFrame()
    
    data = data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    data[['Open', 'High', 'Low', 'Close']] = data[['Open', 'High', 'Low', 'Close']].round(2)
    data['Change(%)'] = (data['Close'].pct_change() * 100).round(2)
    
    data = calculate_moving_averages(data)
    data['RSI'] = calculate_rsi(data)
    
    # 공통 데이터 병합
    if common_data.get('fg_data') is not None:
        data = pd.merge(data, common_data['fg_data'], on='Date', how='left')
    if not common_data.get('vix').empty:
        data = pd.merge(data, common_data['vix'], on='Date', how='left')
    if not common_data.get('vix1d').empty:
        data = pd.merge(data, common_data['vix1d'], on='Date', how='left')
    
    data = generate_fg_rsi_signals(data)
    data['Tick'] = ticker
    
    # 최근 데이터만
    cutoff = datetime.now() - timedelta(days=delta)
    data = data[data['Date'] >= cutoff]
    
    return data

def get_ticker_configs():
    return {
        'SOXL': 'SOXL', '^GSPC': 'S&P500', '^IXIC': 'NASDAQ',
        'SSO': 'SSO', 'QLD': 'QLD', 'TSLA': 'TESLA',
        'GLD': 'GOLD', 'SLV': 'SILVER'
    }