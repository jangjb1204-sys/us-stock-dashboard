"""Find US stocks, ETFs and indexes by ticker, English name or common Korean name.

Used by the US page's search box so people don't have to know the exact
ticker. Names come from Yahoo Finance's symbol search, filtered to US
listings; Yahoo can't read Hangul, so popular Korean names are mapped here.
"""

from __future__ import annotations

import re

import requests

YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"

# Yahoo exchange codes for US listings (NASDAQ tiers, NYSE, NYSE American,
# NYSE Arca, Cboe BZX) and for the US index families.
US_EXCHANGES = {"NMS", "NGM", "NCM", "NAS", "NYQ", "NYS", "ASE", "PCX", "BTS"}
US_INDEX_EXCHANGES = {"SNP", "NIM", "DJI", "WCB", "NYB", "PHL", "CXI"}
TICKER_PATTERN = re.compile(r"^\^?[A-Z][A-Z0-9]{0,5}(?:-[A-Z])?$")
_HANGUL = re.compile(r"[가-힣ㄱ-ㆎ]")

# Korean names people actually type -> ticker. Several names may share one.
KO_ALIASES: dict[str, tuple[str, str]] = {
    "애플": ("AAPL", "Apple Inc."),
    "마이크로소프트": ("MSFT", "Microsoft Corporation"), "마소": ("MSFT", "Microsoft Corporation"),
    "엔비디아": ("NVDA", "NVIDIA Corporation"),
    "테슬라": ("TSLA", "Tesla, Inc."),
    "아마존": ("AMZN", "Amazon.com, Inc."),
    "구글": ("GOOGL", "Alphabet Inc."), "알파벳": ("GOOGL", "Alphabet Inc."),
    "메타": ("META", "Meta Platforms, Inc."), "페이스북": ("META", "Meta Platforms, Inc."),
    "넷플릭스": ("NFLX", "Netflix, Inc."),
    "브로드컴": ("AVGO", "Broadcom Inc."),
    "에이엠디": ("AMD", "Advanced Micro Devices, Inc."),
    "인텔": ("INTC", "Intel Corporation"),
    "퀄컴": ("QCOM", "QUALCOMM Incorporated"),
    "마이크론": ("MU", "Micron Technology, Inc."),
    "대만반도체": ("TSM", "Taiwan Semiconductor Manufacturing"), "티에스엠씨": ("TSM", "Taiwan Semiconductor Manufacturing"),
    "팔란티어": ("PLTR", "Palantir Technologies Inc."),
    "오라클": ("ORCL", "Oracle Corporation"),
    "세일즈포스": ("CRM", "Salesforce, Inc."),
    "어도비": ("ADBE", "Adobe Inc."),
    "슈퍼마이크로": ("SMCI", "Super Micro Computer, Inc."),
    "아이온큐": ("IONQ", "IonQ, Inc."),
    "리게티": ("RGTI", "Rigetti Computing, Inc."),
    "코인베이스": ("COIN", "Coinbase Global, Inc."),
    "스트래티지": ("MSTR", "Strategy Inc"), "마이크로스트래티지": ("MSTR", "Strategy Inc"),
    "우버": ("UBER", "Uber Technologies, Inc."),
    "에어비앤비": ("ABNB", "Airbnb, Inc."),
    "쇼피파이": ("SHOP", "Shopify Inc."),
    "로블록스": ("RBLX", "Roblox Corporation"),
    "쿠팡": ("CPNG", "Coupang, Inc."),
    "알리바바": ("BABA", "Alibaba Group Holding Limited"),
    "코카콜라": ("KO", "The Coca-Cola Company"),
    "펩시": ("PEP", "PepsiCo, Inc."),
    "맥도날드": ("MCD", "McDonald's Corporation"),
    "스타벅스": ("SBUX", "Starbucks Corporation"),
    "나이키": ("NKE", "NIKE, Inc."),
    "디즈니": ("DIS", "The Walt Disney Company"),
    "월마트": ("WMT", "Walmart Inc."),
    "코스트코": ("COST", "Costco Wholesale Corporation"),
    "버크셔": ("BRK-B", "Berkshire Hathaway Inc."),
    "제이피모건": ("JPM", "JPMorgan Chase & Co."), "JP모건": ("JPM", "JPMorgan Chase & Co."),
    "뱅크오브아메리카": ("BAC", "Bank of America Corporation"),
    "비자": ("V", "Visa Inc."),
    "마스터카드": ("MA", "Mastercard Incorporated"),
    "페이팔": ("PYPL", "PayPal Holdings, Inc."),
    "존슨앤존슨": ("JNJ", "Johnson & Johnson"),
    "화이자": ("PFE", "Pfizer Inc."),
    "일라이릴리": ("LLY", "Eli Lilly and Company"), "릴리": ("LLY", "Eli Lilly and Company"),
    "노보노디스크": ("NVO", "Novo Nordisk A/S"),
    "유나이티드헬스": ("UNH", "UnitedHealth Group Incorporated"),
    "엑슨모빌": ("XOM", "Exxon Mobil Corporation"),
    "셰브론": ("CVX", "Chevron Corporation"),
    "보잉": ("BA", "The Boeing Company"),
    # indexes & ETFs
    "에스앤피500": ("SPY", "SPDR S&P 500 ETF"), "S&P500": ("SPY", "SPDR S&P 500 ETF"),
    "나스닥100": ("QQQ", "Invesco QQQ Trust"), "나스닥": ("QQQ", "Invesco QQQ Trust"),
    "다우": ("DIA", "SPDR Dow Jones Industrial Average ETF"),
    "러셀2000": ("IWM", "iShares Russell 2000 ETF"),
    "반도체": ("SOXX", "iShares Semiconductor ETF"),
    "속슬": ("SOXL", "Direxion Daily Semiconductor Bull 3X"), "반도체3배": ("SOXL", "Direxion Daily Semiconductor Bull 3X"),
    "티큐큐큐": ("TQQQ", "ProShares UltraPro QQQ"), "나스닥3배": ("TQQQ", "ProShares UltraPro QQQ"),
    "나스닥3배인버스": ("SQQQ", "ProShares UltraPro Short QQQ"),
    "슈드": ("SCHD", "Schwab U.S. Dividend Equity ETF"),
    "제피": ("JEPI", "JPMorgan Equity Premium Income ETF"), "젭큐": ("JEPQ", "JPMorgan Nasdaq Equity Premium Income ETF"),
    "미국채20년": ("TLT", "iShares 20+ Year Treasury Bond ETF"),
    "금": ("GLD", "SPDR Gold Shares"), "은": ("SLV", "iShares Silver Trust"),
    "비트코인": ("IBIT", "iShares Bitcoin Trust ETF"),
    "미국전체": ("VTI", "Vanguard Total Stock Market ETF"),
}


def normalize(text: str) -> str:
    return "".join(str(text).split()).upper()


def looks_like_ticker(query: str) -> bool:
    return bool(TICKER_PATTERN.match(normalize(query)))


def alias_matches(query: str) -> list[dict]:
    """Korean names containing the query (so "엔비" finds 엔비디아), exact first."""
    q = normalize(query)
    if not q or not _HANGUL.search(q) and q not in {normalize(k) for k in KO_ALIASES}:
        return []
    hits = []
    for key, (symbol, name) in KO_ALIASES.items():
        k = normalize(key)
        if q == k or (len(q) >= 1 and q in k):
            hits.append((0 if q == k else 1, len(k), {"symbol": symbol, "name": name, "kind": "", "exchange": ""}))
    hits.sort(key=lambda h: (h[0], h[1]))
    return [h[2] for h in hits]


def parse_yahoo_quotes(payload: dict) -> list[dict]:
    """US stocks/ETFs (and ^ indexes) from Yahoo's search response."""
    out = []
    for quote_ in (payload or {}).get("quotes") or []:
        symbol = str(quote_.get("symbol") or "").upper()
        kind = quote_.get("quoteType")
        exchange = quote_.get("exchange")
        us_listing = kind in ("EQUITY", "ETF") and exchange in US_EXCHANGES and "." not in symbol
        us_index = kind == "INDEX" and symbol.startswith("^") and exchange in US_INDEX_EXCHANGES
        if not (us_listing or us_index) or not TICKER_PATTERN.match(symbol):
            continue
        name = " ".join(str(quote_.get("longname") or quote_.get("shortname") or symbol).split())
        out.append({"symbol": symbol, "name": name, "kind": kind or "", "exchange": quote_.get("exchDisp") or exchange or ""})
    return out


def yahoo_search(query: str, limit: int = 10) -> list[dict]:
    q = _HANGUL.sub(" ", query)
    q = " ".join(q.split())
    if not q:
        return []
    response = requests.get(
        YAHOO_SEARCH_URL,
        params={"q": q, "quotesCount": limit, "newsCount": 0},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=8,
    )
    response.raise_for_status()
    return parse_yahoo_quotes(response.json())


def merge_results(query: str, aliases: list[dict], yahoo: list[dict], limit: int = 12) -> list[dict]:
    """Aliases, then Yahoo results; one row per symbol; an exact ticker match first."""
    seen, merged = set(), []
    for row in aliases + yahoo:
        if row["symbol"] in seen:
            continue
        seen.add(row["symbol"])
        merged.append(row)
    q = normalize(query)
    merged.sort(key=lambda row: 0 if row["symbol"] == q else 1)  # stable: keeps the rest in order
    return merged[:limit]
