import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests
import json
import numpy as np
import time
import os

# --- 상수 및 설정 ---
SEARCH_DAYS = 365 * 4
DATE_FORMAT = '%Y-%m-%d'
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
)

# --- 데이터 수집 함수 ---
def fetch_fear_and_greed_index(start_date: str) -> pd.DataFrame | None:
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
        return df.sort_values('Date').drop_duplicates('Date', keep='first')
    except Exception:
        return None

def fetch_common_market_data(period: str):
    """메인 페이지에서 한 번만 호출하여 모든 종목 분석에 재사용"""
    results = {}
    tickers = {'^TNX': '10Y Treasury', '^VIX': 'VIX', '^VIX1D': 'VIX1D', '^SKEW': 'SKEW'}
    
    for tk, name in tickers.items():
        try:
            df = yf.Ticker(tk).history(period=period)[['Close']].rename(columns={'Close': name})
            df = df.reset_index()
            df['Date'] = pd.to_datetime(df['Date'].dt.date)
            results[name.lower()] = df
            time.sleep(0.5)
        except:
            results[name.lower()] = pd.DataFrame()

    start_date = (datetime.now() - timedelta(days=SEARCH_DAYS)).strftime(DATE_FORMAT)
    results['fg_data'] = fetch_fear_and_greed_index(start_date)
    return results

def fetch_stock_data(ticker: str, period: str) -> pd.DataFrame:
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period).reset_index()
        if not data.empty:
            data['Date'] = pd.to_datetime(data['Date'].dt.date)
        return data
    except:
        return pd.DataFrame()

# --- 기술적 지표 계산 함수 ---
def calculate_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).round(2)

def calculate_moving_averages(data: pd.DataFrame) -> pd.DataFrame:
    for window in [20, 60, 120, 200]:
        data[f'MA{window}'] = data['Close'].rolling(window=window).mean().round(2)
    return data

# --- 매매 신호 생성 로직 ---
def generate_signals(data: pd.DataFrame) -> pd.DataFrame:
    # 1. FG/RSI Signal
    def fg_rsi_rule(row):
        rsi = row.get('RSI', np.nan)
        fg = row.get('FG index', -1)
        if pd.isna(rsi): return ''
        if rsi >= 60 or (51 <= fg <= 100): return 'BUY STOP'
        if rsi <= 30 or (26 <= fg <= 50): return '2x BUY'
        if rsi <= 20 or (0 <= fg <= 25): return '3x BUY'
        return '1x BUY'
    
    data['FG/RSI signal'] = data.apply(fg_rsi_rule, axis=1)

    # 2. Puddle Signal
    alerts = ['']
    for i in range(1, len(data)):
        row, prev = data.iloc[i], data.iloc[i-1]
        sig = ''
        if row['Close'] < row['MA20'] and prev['Close'] >= prev['MA20']: sig = '1st: MA20'
        if row['Close'] < row['MA60'] and prev['Close'] >= prev['MA60']: sig = '2nd: MA60'
        if row['Close'] < row['MA120'] and prev['Close'] >= prev['MA120']: sig = '3rd: MA120'
        if row['Close'] < row['MA200'] and row['RSI'] <= 30: sig = '4th: MA200/RSI'
        alerts.append(sig)
    data['Puddle'] = alerts

    # 3. VIX Signal
    if 'VIX' in data.columns and 'VIX1D' in data.columns:
        data['VIX1D>VIX'] = np.where((data['VIX'] >= 25) & (data['VIX1D'] > data['VIX']), 'BUY', '')
    
    return data

# --- 메인 분석 함수 (Streamlit에서 호출하는 함수) ---
def get_full_analysis(ticker: str, name: str, common_data: dict, period: str = '4y') -> pd.DataFrame:
    data = fetch_stock_data(ticker, period)
    if data.empty: return pd.DataFrame()

    # 지표 계산
    data[['Close', 'Open', 'High', 'Low']] = data[['Close', 'Open', 'High', 'Low']].round(2)
    data['Change(%)'] = (data['Close'].pct_change() * 100).round(2)
    
    # 2시그마 계산 (통계적 과매도/과매수)
    log_returns = np.log(data['Close'] / data['Close'].shift(1))
    data['2sigma(%)'] = round(log_returns.std() * 100 * 2, 1)

    data = calculate_moving_averages(data)
    data['RSI'] = calculate_rsi(data)

    # 공통 데이터(VIX, 국채 등) 병합
    for key in ['fg_data', 'treasury', 'vix', 'vix1d', 'skew']:
        if common_data.get(key) is not None and not common_data[key].empty:
            data = pd.merge(data, common_data[key], on='Date', how='left')

    
    # 신호 생성
    data = generate_signals(data)
    
    # 불필요한 결측치 처리 및 정리 (최신 Pandas 방식)
    data = data.ffill().fillna('') 
    return data