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
        # 병합을 위해 Date를 문자열로 유지
        return df.sort_values('Date').drop_duplicates('Date')
    except:
        return None

def fetch_common_market_data(period: str):
    results = {}
    tickers = {'^TNX': 'Treasury', '^VIX': 'VIX', '^VIX1D': 'VIX1D'}
    
    for tk, name in tickers.items():
        try:
            # yfinance 데이터 추출
            ticker_obj = yf.Ticker(tk)
            df = ticker_obj.history(period=period)[['Close']].rename(columns={'Close': name})
            
            if tk == '^TNX': 
                df[name] = df[name] / 10.0 # 국채 금리 단위 보정 (4.3% 형태)
                
            df = df.reset_index()
            # [중요] 날짜를 문자열 'YYYY-MM-DD'로 강제 변환하여 타입 통일
            df['Date'] = df['Date'].dt.strftime(DATE_FORMAT)
            results[name.lower()] = df
            time.sleep(0.1)
        except:
            results[name.lower()] = pd.DataFrame()

    start_date = (datetime.now() - timedelta(days=SEARCH_DAYS)).strftime(DATE_FORMAT)
    results['fg_data'] = fetch_fear_and_greed_index(start_date)
    return results

def fetch_stock_data(ticker: str, period: str) -> pd.DataFrame:
    try:
        data = yf.Ticker(ticker).history(period=period).reset_index()
        # [중요] 메인 데이터의 날짜도 문자열 'YYYY-MM-DD'로 강제 변환
        data['Date'] = data['Date'].dt.strftime(DATE_FORMAT)
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
    # 숫자 연산을 위해 컬럼들을 숫자형으로 재확인
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

    # 문자열로 통일된 Date를 기준으로 병합
    for key in ['fg_data', 'treasury', 'vix', 'vix1d']:
        if key in common_data and not common_data[key].empty:
            # 병합 전 타겟 데이터의 날짜도 문자열인지 재확인
            target_df = common_data[key].copy()
            data = pd.merge(data, target_df, on='Date', how='left')

    # 국채 등 공휴일 데이터 채우기
    data = data.ffill()
    return generate_signals(data)