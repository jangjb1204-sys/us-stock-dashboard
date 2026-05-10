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

# 상수 정의
SEARCH_DAYS = 365 * 4
DATE_FORMAT = '%Y-%m-%d'
COLORS = {
    'GREEN': '#008000', 'RED': '#FF0000', 'BLACK': '#000000',
    'YELLOW_FILL': '#FFFF99', 'HEADER_FILL': '#D3D3D3', 'LATEST_FILL': '#E6E6FA',
}
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# ==================== 데이터 수집 ====================
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
    start_date = (datetime.now() - timedelta(days=SEARCH_DAYS)).strftime(DATE_FORMAT)
    fg_data = fetch_fear_and_greed_index(start_date)
    return {'fg_data': fg_data}

def fetch_stock_data(ticker: str, period: str):
    time.sleep(2)
    stock = yf.Ticker(ticker)
    data = stock.history(period=period).reset_index()
    if not data.empty:
        data['Date'] = pd.to_datetime(data['Date'].dt.date)
    return data

# ==================== 기술적 지표 ====================
def calculate_rsi(data: pd.DataFrame, window: int = 14):
    if len(data) < window:
        return pd.Series([np.nan] * len(data))
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
        fg = row.get('FG index', -1)
        if rsi >= 60 or (not pd.isna(fg) and 51 <= fg <= 100):
            return 'BUY STOP'
        elif rsi <= 30 or (not pd.isna(fg) and 26 <= fg <= 50):
            return '2x BUY'
        elif rsi <= 20 or (not pd.isna(fg) and 0 <= fg <= 25):
            return '3x BUY'
        return '1x BUY'
    data['FG/RSI signal'] = data.apply(apply_rules, axis=1)
    return data

# ==================== 파일 저장 함수 (원래 기능 유지) ====================
def create_table_image(data: pd.DataFrame, name: str):
    last_n = data.tail(20).copy()
    last_n['Date'] = last_n['Date'].dt.strftime(DATE_FORMAT)
    fig, ax = plt.subplots(figsize=(16, len(last_n)*0.25))
    ax.axis('off')
    table = ax.table(cellText=last_n.values, colLabels=last_n.columns, loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    save_path = os.path.join(folder_path, f"{name}_table.jpg")
    plt.savefig(save_path, bbox_inches='tight', dpi=200)
    plt.close()

def save_to_excel(data: pd.DataFrame, name: str):
    excel_file = os.path.join(folder_path, f"{name}_table.xlsx")
    data.to_excel(excel_file, index=False)

def create_puddle_trading_chart(data: pd.DataFrame, name: str):
    if data.empty:
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], name='Close'))
    fig.update_layout(title=f"{name} Chart", height=500)
    save_path = os.path.join(folder_path, f"{name}_chart.jpg")
    fig.write_image(save_path, width=800, height=500)

# ==================== 메인 처리 함수 ====================
def process_stock_data(ticker: str, name: str, common_data: dict, period: str = '4y', delta: int = 600):
    data = fetch_stock_data(ticker, period)
    if data.empty:
        print(f"{ticker} 데이터 없음")
        return pd.DataFrame()

    data = data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    data[['Open','High','Low','Close']] = data[['Open','High','Low','Close']].round(2)
    data['Change(%)'] = (data['Close'].pct_change() * 100).round(2)

    data = calculate_moving_averages(data)
    data['RSI'] = calculate_rsi(data)
    data = generate_fg_rsi_signals(data)
    data['Tick'] = ticker

    # 최근 기간만 유지
    cutoff = datetime.now() - timedelta(days=delta)
    data = data[data['Date'] >= cutoff].copy()

    # ==================== 파일 저장 ====================
    if not data.empty:
        try:
            create_table_image(data, name)
            save_to_excel(data, name)
            create_puddle_trading_chart(data, name)
            print(f"✅ {name} 파일 생성 완료")
        except Exception as e:
            print(f"파일 저장 오류 ({name}): {e}")

    return data

def get_ticker_configs():
    return {
        'SOXL': 'SOXL', '^GSPC': 'S&P500', '^IXIC': 'NASDAQ',
        'SSO': 'SSO', 'QLD': 'QLD', 'TSLA': 'TESLA',
        'GLD': 'GOLD', 'SLV': 'SILVER'
    }