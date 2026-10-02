"""Daily scan: KOSPI + KOSDAQ stocks ranked by today's trading value (거래대금),
top N, each run through the 한국 시장 rule (5/10-month base + 60-day disparity).

Runs in GitHub Actions after the KRX close and writes:
  out/kr_top100_latest.csv, out/kr_top100_YYYYMMDD.csv, out/kr_top100_debug.json

Ranking comes from Naver's mobile stock API (all listed stocks, paged), which
reports each stock's accumulated trading value. ETFs/ETNs are excluded.
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import korea_signal_engine as engine  # noqa: E402

TOP_N = 100
PAGE_SIZE = 100
NAVER_URL = "https://m.stock.naver.com/api/stocks/marketValue/{market}"
HEADERS = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
           "Referer": "https://m.stock.naver.com/"}
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
debug: dict = {"started": datetime.now(timezone.utc).isoformat(), "pages": {}, "errors": []}


def num(value) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def fetch_market(market: str) -> list[dict]:
    rows, page = [], 1
    while True:
        resp = requests.get(NAVER_URL.format(market=market), params={"page": page, "pageSize": PAGE_SIZE},
                            headers=HEADERS, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        stocks = payload.get("stocks") or []
        if page == 1:
            debug["pages"][market] = {"keys": sorted(payload.keys()), "total": payload.get("totalCount"),
                                      "sample": stocks[:2]}
        for item in stocks:
            rows.append({
                "code": str(item.get("itemCode") or "").zfill(6),
                "name": item.get("stockName") or "",
                "market": market,
                "end_type": str(item.get("stockEndType") or ""),
                "close": num(item.get("closePrice")),
                "change_pct": num(item.get("fluctuationsRatio")),
                # 백만원 단위 on Naver
                "value_mil": num(item.get("accumulatedTradingValue")),
                "volume": num(item.get("accumulatedTradingVolume")),
            })
        total = payload.get("totalCount") or 0
        if not stocks or page * PAGE_SIZE >= total or page > 40:
            break
        page += 1
        time.sleep(0.15)
    return rows


def ranked_stocks() -> pd.DataFrame:
    frames = [pd.DataFrame(fetch_market(m)) for m in ("KOSPI", "KOSDAQ")]
    df = pd.concat(frames, ignore_index=True).dropna(subset=["value_mil"])
    debug["listed"] = int(len(df))
    debug["end_types"] = df["end_type"].value_counts().to_dict()
    # stocks only: drop ETF/ETN rows (by type when given, by name as a backstop)
    is_fund = df["end_type"].str.lower().isin({"etf", "etn"}) | df["name"].str.contains(
        r"ETN|ETF|KODEX|TIGER|KBSTAR|RISE |ACE |SOL |HANARO|PLUS |KOSEF|ARIRANG", regex=True)
    df = df[~is_fund & (df["code"].str.len() == 6)]
    df = df.sort_values("value_mil", ascending=False).drop_duplicates("code").head(TOP_N).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df


def signal_row(row: dict, today) -> dict:
    out = dict(row)
    suffix = engine.MARKET_SUFFIX.get(row["market"], ".KS")
    try:
        daily, _ = engine.fetch_history(row["code"] + suffix, today.year - 2)
        status = engine.current_status(row["code"], daily, today, label=row["name"])
        out.update({
            "weight": status.final_weight,             # this month (confirmed last month-end, after overheat cut)
            "base_weight": status.base_weight,
            "next_weight": engine.SIGNAL_WEIGHT[status.live_signal],  # next month if the month ended today
            "disparity": round(status.disparity, 1) if status.disparity is not None else None,
            "overheated": bool(status.overlay_active),
            "to_full_pct": round((status.green_above / status.last_close - 1) * 100, 1),
            "to_none_pct": round((status.red_below / status.last_close - 1) * 100, 1),
            "last_date": status.last_date.date().isoformat(),
            "status": "ok",
        })
    except engine.HistoryTooShort:
        out["status"] = "short"
    except Exception as exc:  # keep the row, mark it
        out["status"] = f"error: {type(exc).__name__}"
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    today = engine.kst_today()
    try:
        top = ranked_stocks()
        with ThreadPoolExecutor(max_workers=6) as pool:
            rows = list(pool.map(lambda r: signal_row(r, today), top.to_dict("records")))
        result = pd.DataFrame(rows).sort_values("rank")
        # label with the trading day the prices are from (a holiday run keeps the last session)
        trade_day = result["last_date"].dropna().mode()
        day = pd.Timestamp(trade_day.iloc[0]).date() if len(trade_day) else today
        result.insert(0, "date", day.isoformat())
        result["scanned_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        result.to_csv(OUT / f"kr_top100_{day:%Y%m%d}.csv", index=False, encoding="utf-8")
        result.to_csv(OUT / "kr_top100_latest.csv", index=False, encoding="utf-8")
        debug["rows"] = int(len(result))
        debug["status_counts"] = result["status"].value_counts().to_dict()
    except Exception as exc:
        debug["errors"].append(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        (OUT / "kr_top100_debug.json").write_text(json.dumps(debug, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
