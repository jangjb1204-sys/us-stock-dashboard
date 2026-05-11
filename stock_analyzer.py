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
                'FG index': round(item['y'])
            }
            for item in data_list
        ])
        return df.sort_values('Date').drop_duplicates('Date')
    except:
        return pd.DataFrame(columns=['Date', 'FG index'])

def fetch_common_market_data(period: str):
    results = {}
    tickers = {'^TNX': 'Treasury', '^VIX': 'VIX', '^VIX1D': 'VIX1D'}
    
    for tk, name in tickers.items():
        try:
            df = yf.Ticker(tk).history(period=period)[['Close']].rename(columns={'Close': name})
            if tk == '^TNX': 
                df[name] = df[name] / 10.0
            df = df.reset_index()
            # 병합 전처리: Datetime을 문자열로 고정
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime(DATE_FORMAT)
            results[name.lower()] = df
            time.sleep(0.1)
        except:
            results[name.lower()] = pd.DataFrame(columns=['Date', name])

    start_date = (datetime.now() - timedelta(days=SEARCH_DAYS)).strftime(DATE_FORMAT)
    results['fg_data'] = fetch_fear_and_greed_index(start_date)
    return results

def fetch_stock_data(ticker: str, period: str) -> pd.DataFrame:
    try:
        data = yf.Ticker(ticker).history(period=period).reset_index()
        data['Date'] = pd.to_datetime(data['Date']).dt.strftime(DATE_FORMAT)
        return data
    except:
        return pd.DataFrame()

def calculate_rsi(data: pd.DataFrame, window: int = 14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).round(2)

def calculate_moving_averages(data: pd.DataFrame):
    for w in [20, 60, 120, 200]:
        data[f'MA{w}'] = data['Close'].rolling(window=w).mean().round(2)
    return data

def generate_signals(data: pd.DataFrame):
    numeric_cols = ['Close', 'MA20', 'MA60', 'MA120', 'MA200', 'RSI', 'FG index', 'Treasury']
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')

    def fg_rsi_rule(row):
        try:
            rsi, fg = row['RSI'], row['FG index']
            if pd.isna(rsi) or pd.isna(fg): return ''
            if rsi >= 60 or fg >= 51: return 'BUY STOP'
            if rsi <= 30 or (26 <= fg <= 50): return '2x BUY'
            if rsi <= 20 or fg <= 25: return '3x BUY'
            return '1x BUY'
        except: return ''
    
    data['FG/RSI signal'] = data.apply(fg_rsi_rule, axis=1)

    alerts = ['']
    for i in range(1, len(data)):
        row, prev = data.iloc[i], data.iloc[i-1]
        sig = ''
        try:
            if pd.notna(row['Close']) and pd.notna(row['MA20']):
                if row['Close'] < row['MA20'] and prev['Close'] >= prev['MA20']: sig = '1st: MA20'
                elif row['Close'] < row['MA60'] and prev['Close'] >= prev['MA60']: sig = '2nd: MA60'
                elif row['Close'] < row['MA120'] and prev['Close'] >= prev['MA120']: sig = '3rd: MA120'
                elif row['Close'] < row['MA200'] and row['RSI'] <= 30: sig = '4th: MA200/RSI'
        except: pass
        alerts.append(sig)
    data['Puddle'] = alerts
    return data

def get_full_analysis(ticker: str, name: str, common_data: dict, period: str = '4y') -> pd.DataFrame:
    data = fetch_stock_data(ticker, period)
    if data.empty: return pd.DataFrame()

    data = calculate_moving_averages(data)
    data['RSI'] = calculate_rsi(data)

    # 병합 루프
    for key in ['fg_data', 'treasury', 'vix', 'vix1d']:
        if key in common_data and not common_data[key].empty:
            target_df = common_data[key].copy()
            
            # [에러 해결의 핵심] 병합 직전에 양쪽 Date를 모두 문자열로 강제 변환
            data['Date'] = data['Date'].astype(str)
            target_df['Date'] = target_df['Date'].astype(str)
            
            data = pd.merge(data, target_df, on='Date', how='left')

    # 주말 등 빈 데이터 채우기 (국채 금리 표시를 위해 필수)
    data = data.ffill()
    return generate_signals(data)