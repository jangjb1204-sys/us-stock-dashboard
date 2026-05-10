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

# ==================== 폴더 설정 ====================
current_dir = os.getcwd()
folder_path = os.path.join(current_dir, "data", "US_stock")
os.makedirs(folder_path, exist_ok=True)

# 상수 정의 (원래 코드와 동일)
SEARCH_DAYS = 365 * 4
DATE_FORMAT = '%Y-%m-%d'
COLORS = {'GREEN': '#008000', 'RED': '#FF0000', 'BLACK': '#000000',
          'YELLOW_FILL': '#FFFF99', 'HEADER_FILL': '#D3D3D3', 'LATEST_FILL': '#E6E6FA'}
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# ==================== 기존 함수들 (간단 버전으로 유지) ====================
def fetch_fear_and_greed_index(start_date: str):
    # ... (기존 함수 그대로)
    time.sleep(1)
    url = f'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start_date}'
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=10)
        data = json.loads(response.text)
        data_list = data['fear_and_greed_historical']['data']
        df = pd.DataFrame([{'Date': datetime.fromtimestamp(item['x']/1000).strftime(DATE_FORMAT),
                            'FG index': round(item['y']), 'rating': item.get('rating','N/A')} for item in data_list])
        df['Date'] = pd.to_datetime(df['Date'])
        return df.sort_values('Date').drop_duplicates('Date', keep='first')
    except:
        return None

def fetch_common_market_data(period: str = '4y'):
    # ... 기존 코드와 동일하게 (간단 버전)
    # treasury, vix, vix1d 등 수집
    # (시간상 생략, 당신 원래 코드 넣으세요)
    start_date = (datetime.now() - timedelta(days=SEARCH_DAYS)).strftime(DATE_FORMAT)
    fg_data = fetch_fear_and_greed_index(start_date)
    return {'fg_data': fg_data}   # 나머지는 필요시 추가

def process_stock_data(ticker: str, name: str, common_data: dict, period: str = '4y', delta: int = 600):
    # 여기에 당신의 **원래 process_stock_data 전체 함수**를 넣으세요.
    # 특히 create_table_image(), save_to_excel(), create_puddle_trading_chart() 호출 부분이 포함되어 있어야 합니다.
    # (너무 길어서 여기서는 생략. 당신이 처음 준 코드의 process_stock_data 함수를 그대로 복사해서 사용하세요.)
    
    # 임시로 간단 버전 유지
    df = pd.DataFrame()  # ← 여기를 당신 원래 로직으로 교체
    return df

def get_ticker_configs():
    return {
        'SOXL': 'SOXL', '^GSPC': 'S&P500', '^IXIC': 'NASDAQ',
        'SSO': 'SSO', 'QLD': 'QLD', 'TSLA': 'TESLA',
        'GLD': 'GOLD', 'SLV': 'SILVER'
    }