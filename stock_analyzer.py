import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import yfinance as yf
from datetime import datetime, timedelta
import logging
import requests
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

# Data fetches fail silently by design (the UI just shows N/A rather than
# breaking), but the reason is logged so an outage or an upstream API change is
# diagnosable from the server logs instead of invisible.
logger = logging.getLogger(__name__)

# --- 상수 정의 ---
SEARCH_DAYS = 365 * 4
DATE_FORMAT = '%Y-%m-%d'
# Look-back window (trading days) for the rolling 2-sigma volatility band.
VOLATILITY_WINDOW = 20
CENTRAL_TZ = ZoneInfo('America/Chicago')
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
)


def central_now() -> datetime:
    return datetime.now(CENTRAL_TZ)


def central_today() -> pd.Timestamp:
    return pd.Timestamp(central_now().date())

TICKER_CONFIGS = {
    '^GSPC': 'S&P500',
    '^IXIC': 'NASDAQ',
    'SSO': 'SSO',
    'QLD': 'QLD',
    'SOXL': 'SOXL',
    'KORU': 'KORU',
    'SLV': 'SILVER',
    'GLD': 'GOLD',
    'BTGD': 'BTGD',
    'TSLA': 'TESLA',
}

# --- 데이터 수집 ---
def fetch_fear_and_greed_index(start_date: str) -> pd.DataFrame | None:
    url = f'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start_date}'
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.warning('Fear & Greed fetch returned HTTP %s', response.status_code)
            return None
        data = json.loads(response.text)
        data_list = data['fear_and_greed_historical']['data']
        df = pd.DataFrame([
            {
                'Date': datetime.fromtimestamp(item['x'] / 1000, CENTRAL_TZ).strftime(DATE_FORMAT),
                'FG index': round(item['y']),
                'rating': item.get('rating', 'N/A')
            }
            for item in data_list
        ])
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').drop_duplicates('Date', keep='first')
        return df
    except Exception:
        logger.exception('Fear & Greed fetch failed')
        return None


def fetch_common_market_data(period: str = '2y') -> dict:
    results = {}
    market_specs = [
        ('treasury', '^TNX', '10Y Treasury'),
        ('vix',     '^VIX', 'VIX'),
        ('vix1d',   '^VIX1D', 'VIX1D'),
        ('skew',    '^SKEW', 'SKEW'),
    ]

    try:
        symbols = [ticker_sym for _, ticker_sym, _ in market_specs]
        raw = yf.download(
            tickers=symbols,
            period=period,
            group_by='ticker',
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception:
        logger.exception('Batch download of market indices failed (%s)', symbols)
        raw = pd.DataFrame()

    def normalize_market_frame(ticker_sym: str, col_name: str) -> pd.DataFrame:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                df = raw[ticker_sym][['Close']].dropna(how='all').rename(columns={'Close': col_name})
            else:
                df = raw[['Close']].dropna(how='all').rename(columns={'Close': col_name})
            df = df.reset_index()
            if 'Date' not in df.columns:
                df = df.rename(columns={df.columns[0]: 'Date'})
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None).dt.normalize()
            df[col_name] = df[col_name].round(2)
            return df
        except Exception:
            return pd.DataFrame()

    def fetch_market_series(spec):
        key, ticker_sym, col_name = spec
        df = normalize_market_frame(ticker_sym, col_name)
        if not df.empty:
            return key, df
        try:
            df = yf.Ticker(ticker_sym).history(period=period)[['Close']].rename(columns={'Close': col_name})
            df = df.reset_index()
            df['Date'] = pd.to_datetime(df['Date'].dt.date)
            df[col_name] = df[col_name].round(2)
            return key, df
        except Exception:
            logger.exception('Failed to fetch market series %s (%s)', key, ticker_sym)
            return key, pd.DataFrame()

    with ThreadPoolExecutor(max_workers=len(market_specs)) as executor:
        for key, df in executor.map(fetch_market_series, market_specs):
            results[key] = df

    start_date = (central_now() - timedelta(days=SEARCH_DAYS)).strftime(DATE_FORMAT)
    results['fg_data'] = fetch_fear_and_greed_index(start_date)
    return results


def fetch_stock_data(ticker: str, period: str) -> pd.DataFrame:
    try:
        stock = yf.Ticker(ticker)
        # auto_adjust is set explicitly to stay consistent with
        # fetch_batch_stock_data (used for the market summary table). Leaving it
        # to yfinance's default made the single-ticker view and the summary
        # table disagree on price for dividend-paying ETFs, and that default has
        # changed between yfinance releases.
        data = stock.history(period=period, auto_adjust=False).reset_index()
        if not data.empty:
            data['Date'] = pd.to_datetime(data['Date'].dt.date)
        return data
    except Exception:
        logger.exception('Price history fetch failed for %s', ticker)
        return pd.DataFrame()


def fetch_ticker_display_name(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker).info or {}
        name = info.get('longName') or info.get('shortName') or info.get('displayName')
        return str(name).strip() if name else ticker
    except Exception:
        logger.warning('Display-name lookup failed for %s', ticker, exc_info=True)
        return ticker


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
        logger.exception('Batch price download failed (%s)', tickers)
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
            logger.exception('Failed to normalize batch data for %s', ticker)
            results[ticker] = pd.DataFrame()
    return results


# --- 기술적 지표 계산 ---
# NOTE: main.py and puddle_signal_dashboard.py both import calculate_rsi,
# calculate_moving_averages and generate_puddle_signals from this module.
# Keep this as the single source of truth for indicator/signal logic —
# don't add a second copy in another file.
def calculate_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """Relative Strength Index using Wilder's smoothing (the standard).

    Wilder's RSI is what TradingView, Yahoo Finance and most charting
    platforms display, so values here line up with what you'd see there.
    (A simple rolling mean instead of the EMA below gives "Cutler's RSI",
    which can differ by 20+ points and would desync the 20/30/60
    thresholds this dashboard's signals are built on.)
    """
    if len(data) <= window:
        return pd.Series([np.nan] * len(data), index=data.index)
    delta = data['Close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    def wilder_average(series: pd.Series) -> pd.Series:
        # Wilder seeds the average with the simple mean of the first `window`
        # changes, then smooths recursively. ewm(alpha=1/window, adjust=False)
        # is that same recursion, so seeding position `window` and blanking
        # everything before it reproduces Wilder's values exactly.
        seeded = series.copy()
        seeded.iloc[:window] = np.nan
        seeded.iloc[window] = series.iloc[1:window + 1].mean()
        return seeded.ewm(alpha=1 / window, adjust=False).mean()

    avg_gain = wilder_average(gain)
    avg_loss = wilder_average(loss)
    rs = avg_gain / avg_loss
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
    data = data.copy()
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
        # Order matters: the RSI thresholds overlap (<=20 is also <=30), so the
        # most extreme tier must be tested first. Checking <=30 before <=20
        # made '3x BUY' unreachable via RSI entirely.
        # The market-wide F&G index intentionally takes priority: a greedy
        # market yields 'BUY STOP' even when a single ticker is oversold.
        if rsi >= 60 or (has_fg and 51 <= fg_idx <= 100):
            return 'BUY STOP'
        elif rsi <= 20 or (has_fg and 0 <= fg_idx <= 25):
            return '3x BUY'
        elif rsi <= 30 or (has_fg and 26 <= fg_idx <= 50):
            return '2x BUY'
        return '1x BUY'
    data['FG/RSI signal'] = data.apply(apply_rules, axis=1)
    return data


def generate_puddle_signals(data: pd.DataFrame) -> pd.DataFrame:
    """Detect MA/RSI breakdown ("puddle") signals.

    Canonical implementation — also used by puddle_signal_dashboard.py.
    Do not fork a second copy of this logic; import it from here instead.
    """
    data = data.copy()
    alerts = ['']
    for i in range(1, len(data)):
        row, prev = data.iloc[i], data.iloc[i - 1]
        conditions = {
            1: (
                pd.notna(row.get('MA20')) and pd.notna(prev.get('MA20'))
                and row['Close'] < row['MA20'] and prev['Close'] >= prev['MA20']
            ),
            2: (
                pd.notna(row.get('MA60')) and pd.notna(prev.get('MA60'))
                and row['Close'] < row['MA60'] and prev['Close'] >= prev['MA60']
            ),
            3: (
                pd.notna(row.get('MA120')) and pd.notna(prev.get('MA120'))
                and row['Close'] < row['MA120'] and prev['Close'] >= prev['MA120']
            ),
            4: (
                pd.notna(row.get('MA200')) and pd.notna(prev.get('MA200'))
                and row['Close'] < row['MA200'] and prev['Close'] >= prev['MA200']
                and pd.notna(row.get('RSI')) and row['RSI'] < 30
            ),
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
    # Rolling 2-sigma band: each row reflects volatility over the preceding
    # VOLATILITY_WINDOW trading days. (Previously this was a single whole-series
    # std copied onto every row, so the column never varied by date and ignored
    # the range the user had selected.)
    log_returns = np.log(data['Close'] / data['Close'].shift(1))
    data['2sigma(%)'] = (
        log_returns.rolling(window=VOLATILITY_WINDOW).std() * 100 * 2
    ).round(1)

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
        data = data[data['Date'] >= central_today() - pd.Timedelta(days=delta)]

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
