import pandas as pd
import yfinance as yf
import numpy as np
import requests
import json
import time
from datetime import datetime, timedelta

class StockAnalyzer:
    def __init__(self):
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
        self.date_format = '%Y-%m-%d'

    def fetch_fear_and_greed(self):
        start_date = (datetime.now() - timedelta(days=365 * 4)).strftime(self.date_format)
        url = f'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start_date}'
        headers = {'User-Agent': self.user_agent}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = json.loads(response.text)
                df = pd.DataFrame([{
                    'Date': datetime.fromtimestamp(item['x'] / 1000).strftime(self.date_format),
                    'FG index': round(item['y']),
                    'rating': item.get('rating', 'N/A')
                } for item in data['fear_and_greed_historical']['data']])
                df['Date'] = pd.to_datetime(df['Date'])
                return df.sort_values('Date').drop_duplicates('Date', keep='first')
        except:
            return pd.DataFrame()

    def get_market_indicators(self, period='4y'):
        indicators = {'^VIX': 'VIX', '^VIX1D': 'VIX1D', '^TNX': '10Y Treasury', '^SKEW': 'SKEW'}
        combined_df = pd.DataFrame()
        
        for ticker, name in indicators.items():
            try:
                data = yf.Ticker(ticker).history(period=period)[['Close']].rename(columns={'Close': name})
                data.index = pd.to_datetime(data.index.date)
                if combined_df.empty:
                    combined_df = data
                else:
                    combined_df = combined_df.join(data, how='outer')
            except:
                continue
        return combined_df.reset_index().rename(columns={'index': 'Date'})

    def calculate_metrics(self, df):
        # 이동평균
        for w in [20, 60, 120, 200]:
            df[f'MA{w}'] = df['Close'].rolling(window=w).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = (100 - (100 / (1 + (gain / loss)))).round(2)
        
        # Change & Sigma
        df['Change(%)'] = (df['Close'].pct_change() * 100).round(2)
        df['2sigma(%)'] = round(np.log(df['Close'] / df['Close'].shift(1)).std() * 100 * 2, 1)
        
        # Puddle Signal
        p_alerts = ['']
        for i in range(len(df)):
            if i == 0: continue
            row, prev = df.iloc[i], df.iloc[i-1]
            res = ''
            if row['Close'] < row['MA20'] <= prev['Close']: res = '1st: MA20'
            elif row['Close'] < row['MA60'] <= prev['Close']: res = '2nd: MA60'
            elif row['Close'] < row['MA120'] <= prev['Close']: res = '3rd: MA120'
            elif row['Close'] < row['MA200'] and row['RSI'] <= 30: res = '4th: MA200'
            p_alerts.append(res)
        df['Puddle'] = p_alerts
        return df