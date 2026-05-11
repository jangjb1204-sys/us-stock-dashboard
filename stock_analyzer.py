import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests
import json
import numpy as np
import time

# --- 설정 ---
SEARCH_DAYS = 365 * 4
DATE_FORMAT = '%Y-%m-%d'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'

def fetch_fear_and_greed_index(start_date: str) -> pd.DataFrame | None:
    url = f'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start_date}'
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=10)
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
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None).dt.normalize()
        return df.sort_values('Date').drop_duplicates('Date')
    except:
        return None

def fetch_common_market_data(period: str):
    results = {}
    tickers = {'^TNX': 'Treasury', '^VIX': 'VIX', '^VIX1D': 'VIX1D', '^SKEW': 'SKEW'}
    
    for tk, name in tickers.items():
        try:
            df = yf.Ticker(tk).history(period=period)[['Close']].rename(columns={'Close': name})
            if tk == '^TNX': df[name] = df[name] / 10.0
            df = df.reset_index()
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None).dt.normalize()
            results[name.lower()] = df
            time.sleep(0.2)
        except:
            results[name.lower()] = pd.DataFrame()

    start_date = (datetime.now() - timedelta(days=SEARCH_DAYS)).strftime(DATE_FORMAT)
    results['fg_data'] = fetch_fear_and_greed_index(start_date)
    return results

def fetch_stock_data(ticker: str, period: str) -> pd.DataFrame:
    try:
        data = yf.Ticker(ticker).history(period=period).reset_index()
        data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None).dt.normalize()
        return data
    except:
        return pd.DataFrame()

def calculate_rsi(data: pd.DataFrame, window: int = 14):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).round(2)

def calculate_moving_averages(data: pd.DataFrame):
    for w in [20, 60, 120, 200]:
        data[f'MA{w}'] = data['Close'].rolling(window=w).mean().round(2)
    return data

def generate_signals(data: pd.DataFrame):
    # 숫자 비교를 위해 모든 대상 컬럼을 강제로 숫자형 변환
    numeric_cols = ['Close', 'MA20', 'MA60', 'MA120', 'MA200', 'RSI', 'FG index', 'VIX', 'VIX1D']
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')

    def fg_rsi_rule(row):
        try:
            rsi = row['RSI']
            fg = row['FG index']
            if pd.isna(rsi) or pd.isna(fg): return ''
            if rsi >= 60 or (51 <= fg <= 100): return 'BUY STOP'
            if rsi <= 30 or (26 <= fg <= 50): return '2x BUY'
            if rsi <= 20 or (0 <= fg <= 25): return '3x BUY'
            return '1x BUY'
        except: return ''
    
    data['FG/RSI signal'] = data.apply(fg_rsi_rule, axis=1)

    alerts = ['']
    for i in range(1, len(data)):
        row, prev = data.iloc[i], data.iloc[i-1]
        sig = ''
        try:
            # 모든 피연산자가 유효한 숫자인지 체크 후 비교
            if pd.notna(row['Close']) and pd.notna(row['MA20']) and pd.notna(prev['Close']):
                if row['Close'] < row['MA20'] and prev['Close'] >= prev['MA20']: sig = '1st: MA20'
                elif row['Close'] < row['MA60'] and prev['Close'] >= prev['MA60']: sig = '2nd: MA60'
                elif row['Close'] < row['MA120'] and prev['Close'] >= prev['MA120']: sig = '3rd: MA120'
                elif row['Close'] < row['MA200'] and row['RSI'] <= 30: sig = '4th: MA200/RSI'
        except: pass
        alerts.append(sig)
    data['Puddle'] = alerts

    if 'VIX' in data.columns and 'VIX1D' in data.columns:
        data['VIX1D>VIX'] = np.where((data['VIX'] >= 25) & (data['VIX1D'] > data['VIX']), 'BUY', '')
    
    return data

def get_full_analysis(ticker: str, name: str, common_data: dict, period: str = '4y') -> pd.DataFrame:
    data = fetch_stock_data(ticker, period)
    if data.empty: return pd.DataFrame()

    data = calculate_moving_averages(data)
    data['RSI'] = calculate_rsi(data)

    for key in ['fg_data', 'treasury', 'vix', 'vix1d', 'skew']:
        if key in common_data and not common_data[key].empty:
            data = pd.merge(data, common_data[key], on='Date', how='left')

    data = data.ffill() # 숫자형 유지를 위해 ffill만 수행
    return generate_signals(data)