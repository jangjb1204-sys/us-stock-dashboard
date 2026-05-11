import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import yfinance as yf
from datetime import datetime, timedelta
import requests
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# --- 상수 정의 ---
SEARCH_DAYS = 365 * 4
DATE_FORMAT = '%Y-%m-%d'
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
)

TICKER_CONFIGS = {
    'SOXL': 'SOXL',
    '^GSPC': 'S&P500',
    '^IXIC': 'NASDAQ',
    'SSO': 'SSO',
    'QLD': 'QLD',
    'GLD': 'GOLD',
    'FINX': 'FINX',
    'BTGD': 'BTGD',
    'SLV': 'SILVER',
    'KORU': 'KORU',
    'TSLA': 'TESLA',
}

# --- 데이터 수집 ---
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
        df = df.sort_values('Date').drop_duplicates('Date', keep='first')
        return df
    except Exception:
        return None


def fetch_common_market_data(period: str = '2y') -> dict:
    results = {}
    market_specs = [
        ('treasury', '^TNX', '10Y Treasury'),
        ('vix',     '^VIX', 'VIX'),
        ('vix1d',   '^VIX1D', 'VIX1D'),
        ('skew',    '^SKEW', 'SKEW'),
    ]

    def fetch_market_series(spec):
        key, ticker_sym, col_name = spec
        try:
            df = yf.Ticker(ticker_sym).history(period=period)[['Close']].rename(columns={'Close': col_name})
            df = df.reset_index()
            df['Date'] = pd.to_datetime(df['Date'].dt.date)
            df[col_name] = df[col_name].round(2)
            return key, df
        except Exception:
            return key, pd.DataFrame()

    with ThreadPoolExecutor(max_workers=len(market_specs)) as executor:
        for key, df in executor.map(fetch_market_series, market_specs):
            results[key] = df

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
    except Exception:
        return pd.DataFrame()


def fetch_batch_stock_data(tickers: list[str], period: str) -> dict[str, pd.DataFrame]:
    try:
        raw = yf.download(
            tickers=tickers,
            period=period,
            group_by='ticker',
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception:
        return {ticker: pd.DataFrame() for ticker in tickers}

    results = {}
    for ticker in tickers:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                data = raw[ticker].dropna(how='all').reset_index()
            else:
                data = raw.dropna(how='all').reset_index()
            if data.empty:
                results[ticker] = pd.DataFrame()
                continue
            if 'Date' not in data.columns:
                data = data.rename(columns={data.columns[0]: 'Date'})
            data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None).dt.normalize()
            results[ticker] = data
        except Exception:
            results[ticker] = pd.DataFrame()
    return results


# --- 기술적 지표 계산 ---
def calculate_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    if len(data) < window:
        return pd.Series([np.nan] * len(data), index=data.index)
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).round(2)


def calculate_stochastic_slow(data: pd.DataFrame, n: int = 14, m: int = 3, t: int = 3):
    if len(data) < n:
        nan_s = pd.Series([np.nan] * len(data), index=data.index)
        return nan_s, nan_s.copy()
    low_min = data['Low'].rolling(window=n).min()
    high_max = data['High'].rolling(window=n).max()
    k_fast = 100 * ((data['Close'] - low_min) / (high_max - low_min))
    slow_k = k_fast.rolling(window=m).mean().round(2)
    slow_d = slow_k.rolling(window=t).mean().round(2)
    return slow_k, slow_d


def calculate_moving_averages(data: pd.DataFrame, windows: list = [20, 60, 120, 200]) -> pd.DataFrame:
    for window in windows:
        data[f'MA{window}'] = data['Close'].rolling(window=window).mean().round(2) if len(data) >= window else np.nan
    return data


# --- 매매 신호 생성 ---
def generate_stochastic_signals(data: pd.DataFrame) -> pd.DataFrame:
    data['SS Signal'] = ''
    if 'Slow_K' in data.columns and 'Slow_D' in data.columns:
        data.loc[
            (data['Slow_K'].shift(1) < data['Slow_D'].shift(1)) & (data['Slow_K'] > data['Slow_D']),
            'SS Signal'
        ] = 'Buy'
        data.loc[
            (data['Slow_K'].shift(1) > data['Slow_D'].shift(1)) & (data['Slow_K'] < data['Slow_D']),
            'SS Signal'
        ] = 'Sell'
    return data


def generate_fg_rsi_signals(data: pd.DataFrame) -> pd.DataFrame:
    def apply_rules(row):
        if pd.isna(row.get('RSI')):
            return ''
        rsi = row['RSI']
        fg_idx = row.get('FG index', -1)
        has_fg = not pd.isna(fg_idx) and fg_idx != -1
        if rsi >= 60 or (has_fg and 51 <= fg_idx <= 100):
            return 'BUY STOP'
        elif rsi <= 30 or (has_fg and 26 <= fg_idx <= 50):
            return '2x BUY'
        elif rsi <= 20 or (has_fg and 0 <= fg_idx <= 25):
            return '3x BUY'
        return '1x BUY'
    data['FG/RSI signal'] = data.apply(apply_rules, axis=1)
    return data


def generate_puddle_signals(data: pd.DataFrame) -> pd.DataFrame:
    alerts = ['']
    for i in range(1, len(data)):
        row, prev = data.iloc[i], data.iloc[i - 1]
        conditions = {
            1: (not pd.isna(row.get('MA20')) and row['Close'] < row['MA20'] and prev['Close'] >= prev.get('MA20', np.nan)),
            2: (not pd.isna(row.get('MA60')) and row['Close'] < row['MA60'] and prev['Close'] >= prev.get('MA60', np.nan)),
            3: (not pd.isna(row.get('MA120')) and row['Close'] < row['MA120'] and prev['Close'] >= prev.get('MA120', np.nan)),
            4: (not pd.isna(row.get('MA200')) and row['Close'] < row['MA200'] and
                not pd.isna(row.get('RSI')) and row['RSI'] < 30)
        }
        timings = [k for k, v in conditions.items() if v]
        alerts.append({
            4: '4th: MA200, RSI≤30, 100% cash, 40d',
            3: '3rd: MA120, 50% cash, 5d',
            2: '2nd: MA60, 50% cash, 5d',
            1: '1st: MA20, 10% cash'
        }.get(max(timings)) if timings else '')
    data['Puddle'] = alerts
    return data


def calculate_vix_skew_signals(data: pd.DataFrame) -> pd.DataFrame:
    if 'VIX' in data.columns and 'VIX1D' in data.columns:
        data['VIX1D>VIX'] = np.where(
            data['VIX'].notna() & data['VIX1D'].notna() &
            (data['VIX'] >= 25) & (data['VIX1D'] > data['VIX']),
            'BUY', ''
        )
    else:
        data['VIX1D>VIX'] = ''
    return data


def process_stock_frame(data: pd.DataFrame, ticker: str, name: str, common_data: dict,
                        delta: int = 400) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame()

    fg_data      = common_data.get('fg_data')
    treasury_data = common_data.get('treasury')
    vix_data     = common_data.get('vix')
    vix1d_data   = common_data.get('vix1d')
    skew_data    = common_data.get('skew')

    data[['Close', 'Open', 'High', 'Low']] = data[['Close', 'Open', 'High', 'Low']].round(2)
    data['Change(%)'] = (data['Close'].pct_change() * 100).round(2)
    log_returns = np.log(data['Close'] / data['Close'].shift(1))
    data['2sigma(%)'] = round(log_returns.std() * 100 * 2, 1)

    data = calculate_moving_averages(data)
    data['RSI'] = calculate_rsi(data)
    data['Slow_K'], data['Slow_D'] = calculate_stochastic_slow(data)

    for df_extra in [fg_data, treasury_data, vix_data, vix1d_data, skew_data]:
        if df_extra is not None and not df_extra.empty:
            data = pd.merge(data, df_extra, on='Date', how='left')

    data = generate_stochastic_signals(data)
    data = generate_fg_rsi_signals(data)
    data = generate_puddle_signals(data)
    data = calculate_vix_skew_signals(data)

    if len(data) > delta:
        data = data[data['Date'] >= (datetime.now() - timedelta(days=delta))]

    data['Tick'] = ticker

    target_columns = [
        'Tick', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Change(%)', '2sigma(%)',
        'MA20', 'MA60', 'MA120', 'MA200', 'RSI', 'Slow_K', 'Slow_D',
        'FG index', 'rating', 'FG/RSI signal', 'SS Signal',
        'Puddle', '10Y Treasury', 'VIX', 'VIX1D', 'VIX1D>VIX', 'SKEW'
    ]
    existing_cols = [c for c in target_columns if c in data.columns]
    data_out = data[existing_cols].copy()
    for col in target_columns:
        if col not in data_out.columns:
            data_out[col] = np.nan
    data_out = data_out[target_columns]
    data_out = data_out.reset_index(drop=True)
    return data_out


# --- 메인 처리 함수 ---
def process_stock_data(ticker: str, name: str, common_data: dict,
                       period: str = '2y', delta: int = 400) -> pd.DataFrame:
    data = fetch_stock_data(ticker, period)
    return process_stock_frame(data, ticker, name, common_data, delta=delta)
