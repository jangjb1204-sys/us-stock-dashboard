import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests
import json
import numpy as np
import time

# --- 상수 정의 ---
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
        df['Date'] = pd.to_datetime(df['Date'])
        return df.sort_values('Date').drop_duplicates('Date')
    except:
        return pd.DataFrame(columns=['Date', 'FG index', 'rating'])

def fetch_common_market_data(period: str):
    results = {}
    tickers = {'^TNX': '10Y Treasury', '^VIX': 'VIX', '^VIX1D': 'VIX1D', '^SKEW': 'SKEW'}
    
    for tk, name in tickers.items():
        try:
            df = yf.Ticker(tk).history(period=period)[['Close']].rename(columns={'Close': name})
            if tk == '^TNX': df[name] = (df[name] / 10.0).round(2)
            else: df[name] = df[name].round(1)
            df = df.reset_index()
            df['Date'] = pd.to_datetime(df['Date'].dt.date)
            results[name.lower()] = df
            time.sleep(0.1)
        except:
            results[name.lower()] = pd.DataFrame()

    start_date = (datetime.now() - timedelta(days=SEARCH_DAYS)).strftime(DATE_FORMAT)
    results['fg_data'] = fetch_fear_and_greed_index(start_date)
    return results

def calculate_stochastic_slow(data: pd.DataFrame, n=14, m=3, t=3):
    low_min = data['Low'].rolling(window=n).min()
    high_max = data['High'].rolling(window=n).max()
    k_fast = 100 * ((data['Close'] - low_min) / (high_max - low_min))
    slow_k = k_fast.rolling(window=m).mean().round(2)
    slow_d = slow_k.rolling(window=t).mean().round(2)
    return slow_k, slow_d

def get_full_analysis(ticker: str, common_data: dict, period: str = '4y') -> pd.DataFrame:
    # 1. 주식 기본 데이터
    try:
        data = yf.Ticker(ticker).history(period=period).reset_index()
        data['Date'] = pd.to_datetime(data['Date'].dt.date)
    except:
        return pd.DataFrame()

    # 2. 기술적 지표 계산 (Change, 2sigma, MA, RSI, Stochastic)
    data[['Open', 'High', 'Low', 'Close']] = data[['Open', 'High', 'Low', 'Close']].round(2)
    data['Change(%)'] = (data['Close'].pct_change() * 100).round(2)
    log_returns = np.log(data['Close'] / data['Close'].shift(1))
    data['2sigma(%)'] = round(log_returns.std() * 100 * 2, 1)

    for w in [20, 60, 120, 200]:
        data[f'MA{w}'] = data['Close'].rolling(window=w).mean().round(2)
    
    # RSI
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    data['RSI'] = (100 - (100 / (1 + (gain / loss)))).round(2)
    
    # Stochastic Slow
    data['Slow_K'], data['Slow_D'] = calculate_stochastic_slow(data)

    # 3. 공통 데이터 병합 (Date 기준 타입 통일)
    data['Date'] = pd.to_datetime(data['Date'])
    for key in ['fg_data', '10y treasury', 'vix', 'vix1d', 'skew']:
        target_df = common_data.get(key)
        if target_df is not None and not target_df.empty:
            target_df['Date'] = pd.to_datetime(target_df['Date'])
            data = pd.merge(data, target_df, on='Date', how='left')

    data = data.ffill()

    # 4. 신호 생성 로직 (Puddle, VIX, FG/RSI, SS Signal)
    # Stochastic Signal
    data['SS Signal'] = ''
    data.loc[(data['Slow_K'].shift(1) < data['Slow_D'].shift(1)) & (data['Slow_K'] > data['Slow_D']), 'SS Signal'] = 'Buy'
    data.loc[(data['Slow_K'].shift(1) > data['Slow_D'].shift(1)) & (data['Slow_K'] < data['Slow_D']), 'SS Signal'] = 'Sell'

    # Puddle Signal
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

    # VIX Signal
    data['VIX1D>VIX'] = ''
    if 'VIX' in data.columns and 'VIX1D' in data.columns:
        data.loc[(data['VIX'] >= 25) & (data['VIX1D'] > data['VIX']), 'VIX1D>VIX'] = 'BUY'

    # FG/RSI Signal
    def fg_rsi_rule(row):
        rsi, fg = row.get('RSI'), row.get('FG index')
        if pd.isna(rsi): return ''
        fg_val = fg if pd.notna(fg) else -1
        if rsi >= 60 or 51 <= fg_val <= 100: return 'BUY STOP'
        if rsi <= 30 or 26 <= fg_val <= 50: return '2x BUY'
        if rsi <= 20 or 0 <= fg_val <= 25: return '3x BUY'
        return '1x BUY'
    data['FG/RSI signal'] = data.apply(fg_rsi_rule, axis=1)

    return data