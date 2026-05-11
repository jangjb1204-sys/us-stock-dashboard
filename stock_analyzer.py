import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests
import json
import numpy as np
import time

# --- 설정 및 상수 ---
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
    # 티커 매핑
    tickers = {'^TNX': 'Treasury', '^VIX': 'VIX', '^VIX1D': 'VIX1D', '^SKEW': 'SKEW'}
    
    for tk, name in tickers.items():
        try:
            df = yf.Ticker(tk).history(period=period)[['Close']].rename(columns={'Close': name})
            if tk == '^TNX': df[name] = df[name] / 10.0 # 단위 보정
            df = df.reset_index()
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None).dt.normalize()
            results[name.lower()] = df
            time.sleep(0.1)
        except:
            results[name.lower()] = pd.DataFrame()

    start_date = (datetime.now() - timedelta(days=SEARCH_DAYS)).strftime(DATE_FORMAT)
    results['fg_data'] = fetch_fear_and_greed_index(start_date)
    return results

def get_full_analysis(ticker: str, common_data: dict, period: str = '4y') -> pd.DataFrame:
    # 1. 주식 데이터 수집
    try:
        data = yf.Ticker(ticker).history(period=period).reset_index()
        data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None).dt.normalize()
    except:
        return pd.DataFrame()

    # 2. 지표 계산
    # 이동평균선
    for w in [20, 60, 120, 200]:
        data[f'MA{w}'] = data['Close'].rolling(window=w).mean().round(2)
    
    # RSI
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    data['RSI'] = (100 - (100 / (1 + (gain / loss)))).round(2)

    # 3. 데이터 병합
    for key in ['fg_data', 'treasury', 'vix', 'vix1d', 'skew']:
        if key in common_data and not common_data[key].empty:
            target_df = common_data[key].copy()
            target_df['Date'] = pd.to_datetime(target_df['Date']).dt.tz_localize(None).dt.normalize()
            data = pd.merge(data, target_df, on='Date', how='left')

    data = data.ffill() # 주말 등 결측치 채우기

    # 4. 신호 생성
    # Puddle 신호
    alerts = ['']
    for i in range(1, len(data)):
        row, prev = data.iloc[i], data.iloc[i-1]
        sig = ''
        if row['Close'] < row['MA20'] and prev['Close'] >= prev['MA20']: sig = '1st: MA20'
        elif row['Close'] < row['MA60'] and prev['Close'] >= prev['MA60']: sig = '2nd: MA60'
        elif row['Close'] < row['MA120'] and prev['Close'] >= prev['MA120']: sig = '3rd: MA120'
        elif row['Close'] < row['MA200'] and row['RSI'] <= 30: sig = '4th: MA200/RSI'
        alerts.append(sig)
    data['Puddle'] = alerts

    # VIX 신호
    if 'VIX' in data.columns and 'VIX1D' in data.columns:
        data['VIX1D>VIX'] = np.where((data['VIX'] >= 25) & (data['VIX1D'] > data['VIX']), 'BUY', '')
    
    # FG/RSI 전략
    def strategy(row):
        try:
            rsi, fg = row['RSI'], row.get('FG index', 50)
            if rsi <= 20 or fg <= 25: return '3x BUY'
            if rsi <= 30 or fg <= 50: return '2x BUY'
            if rsi >= 60 or fg >= 51: return 'BUY STOP'
            return '1x BUY'
        except: return ''
    data['FG/RSI signal'] = data.apply(strategy, axis=1)

    return data