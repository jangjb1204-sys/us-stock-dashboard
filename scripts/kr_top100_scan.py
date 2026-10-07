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
ETF_TOP_N = 30
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


# ── Naver themes (mobile API) ─────────────────────────────────────────────────
# Naver lists themes by today's change (strongest first); each stock gets the
# first theme it belongs to in that order, skipping themes that say nothing.
THEME_LIST_URL = "https://m.stock.naver.com/api/stocks/theme"
THEME_MEMBERS_URL = "https://m.stock.naver.com/api/stocks/theme/{no}"
GENERIC_THEME = r"밸류업|S7|신규상장|스팩|SPAC|대표주|우선주|코스피200|외국인|기관|지주사"


def fetch_themes() -> dict[str, str]:
    """code → today's strongest meaningful theme (short name)."""
    import re
    groups: list[dict] = []
    for page in range(1, 15):
        resp = requests.get(THEME_LIST_URL, params={"page": page, "pageSize": 100}, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        batch = resp.json().get("groups") or []
        groups.extend(batch)
        if len(batch) < 100:
            break
        time.sleep(0.15)
    groups = [g for g in groups if g.get("name") and not re.search(GENERIC_THEME, g["name"])]
    debug["themes_found"] = len(groups)

    def members(group):
        try:
            resp = requests.get(THEME_MEMBERS_URL.format(no=group["no"]), params={"page": 1, "pageSize": 100},
                                headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return [str(x.get("itemCode") or "") for x in resp.json().get("stocks") or []]
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=4) as pool:
        member_lists = list(pool.map(members, groups))
    best: dict[str, str] = {}
    for group, codes in zip(groups, member_lists):  # groups are in today's order
        name = re.sub(r"\s*\(.*?\)", "", " ".join(str(group["name"]).split())).strip()
        for code in codes:
            if code and code not in best:
                best[code] = name
    debug["theme_codes"] = len(best)
    return best


def listed_all() -> pd.DataFrame:
    frames = [pd.DataFrame(fetch_market(m)) for m in ("KOSPI", "KOSDAQ")]
    return pd.concat(frames, ignore_index=True).dropna(subset=["value_mil"])


def ranked_stocks(df: pd.DataFrame) -> pd.DataFrame:
    debug["listed"] = int(len(df))
    debug["end_types"] = df["end_type"].value_counts().to_dict()
    # stocks only: drop ETF/ETN rows (by type when given, by name as a backstop)
    is_fund = df["end_type"].str.lower().isin({"etf", "etn"}) | df["name"].str.contains(
        r"ETN|ETF|KODEX|TIGER|KBSTAR|RISE |ACE |SOL |HANARO|PLUS |KOSEF|ARIRANG", regex=True)
    df = df[~is_fund & (df["code"].str.len() == 6)]
    df = df.sort_values("value_mil", ascending=False).drop_duplicates("code").head(TOP_N).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df


# ── ETFs: each kind gets its own basis ─────────────────────────────────────────
CASH_LIKE = r"CD금리|KOFR|SOFR|머니마켓|MMF|국고채|국채|채권|금리|단기|회사채|크레딧|통안|은행채|특수채|전단채"
DOMESTIC_INDEX = r"200|코스피|KOSPI|코스닥|KOSDAQ|KRX\s?300|TOP\s?10|밸류업"
SECTOR_HINT = r"단일종목|반도체|은행|바이오|헬스|2차전지|자동차|증권|건설|철강|IT|미디어|게임|조선|방산|화학|에너지|소비|리츠|로봇|AI|원자력|전력"
FOREIGN_HINT = r"미국|나스닥|S&P|차이나|중국|일본|인도|베트남|유로|글로벌|선진|신흥|원유|금|은|구리|달러|엔"


def etf_kind(name: str) -> tuple[str, str | None]:
    """(kind, underlying index key or None). Kinds: cash, inverse, leverage, index, own."""
    import re
    if re.search(CASH_LIKE, name):
        return "cash", None
    foreign = re.search(FOREIGN_HINT, name)
    sector = re.search(SECTOR_HINT, name)
    domestic = re.search(DOMESTIC_INDEX, name) and not foreign and not sector
    # plain "KODEX 레버리지" / "KODEX 인버스" track KOSPI 200
    plain_kospi_derivative = re.search(r"레버리지|인버스", name) and not foreign and not sector
    underlying = None
    if domestic or plain_kospi_derivative:
        underlying = "KOSDAQ" if re.search(r"코스닥|KOSDAQ", name) else "KOSPI"
    if "인버스" in name:
        return "inverse", underlying
    if "레버리지" in name or re.search(r"2X", name, re.I):
        return "leverage", underlying
    if domestic and not sector:
        return "index", underlying
    return "own", None


def one_step_down(weight: float) -> float:
    """Leveraged ETFs: hold only on a full (100%) signal; 50% → 0%."""
    return 1.0 if weight >= 1.0 else 0.0


def etf_rows(df: pd.DataFrame, today) -> pd.DataFrame:
    etfs = df[df["end_type"].str.lower().eq("etf")].copy()
    etfs["kind"], etfs["underlying"] = zip(*etfs["name"].map(etf_kind)) if len(etfs) else ([], [])
    debug["etf_kinds_all"] = etfs["kind"].value_counts().to_dict()
    etfs = etfs[etfs["kind"] != "cash"].sort_values("value_mil", ascending=False).head(ETF_TOP_N).reset_index(drop=True)
    etfs.insert(0, "rank", range(1, len(etfs) + 1))

    index_status = {}
    for key, cfg in engine.INDEXES.items():
        try:
            daily, _ = engine.fetch_history(cfg["symbol"], today.year - 2)
            index_status[key] = engine.current_status(key, daily, today)
        except Exception as exc:
            debug["errors"].append(f"index {key}: {type(exc).__name__}")

    out = []
    for row in etfs.to_dict("records"):
        kind, und = row["kind"], row["underlying"]
        rec = dict(row)
        base = index_status.get(und) if und else None
        if kind in ("index", "leverage", "inverse") and base is not None:
            w, nxt = base.final_weight, engine.SIGNAL_WEIGHT[base.live_signal]
            rec.update({"basis": f"{engine.INDEXES[und]['label']} 지수",
                        "disparity": round(base.disparity, 1) if base.disparity is not None else None,
                        "overheated": bool(base.overlay_active), "last_date": base.last_date.date().isoformat()})
            if kind == "index":
                rec.update({"weight": w, "next_weight": nxt, "status": "ok"})
            elif kind == "leverage":
                rec.update({"weight": one_step_down(w), "next_weight": one_step_down(nxt), "status": "ok",
                            "note": "100%일 때만 보유"})
            else:  # inverse: reference only, no weight
                rec.update({"weight": None, "next_weight": None, "status": "ref",
                            "note": f"기초지수 {int(round(w * 100))}%"})
        else:
            r = signal_row(row, today)
            r["basis"] = "자체 가격"
            if kind == "leverage" and r.get("status") == "ok":
                r["weight"], r["next_weight"] = one_step_down(r["weight"]), one_step_down(r["next_weight"])
                r["note"] = "100%일 때만 보유"
            if kind == "inverse" and r.get("status") == "ok":
                r.update({"weight": None, "next_weight": None, "status": "ref", "note": "인버스 · 참고만"})
            rec = r
            rec["kind"] = kind
        out.append(rec)
    return pd.DataFrame(out)


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
            "full_line": round(status.green_above, 2),   # price the month-end close must reach for 100%
            "none_line": round(status.red_below, 2),     # below this at month-end → 0%
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
        listed = listed_all()
        if listed.empty or listed["value_mil"].fillna(0).sum() <= 0:
            # before the open Naver reports no trading value yet: keep yesterday's files
            debug["errors"].append("no trading value yet (pre-market) — previous scan kept")
            print("No trading value yet; keeping the previous scan.")
            return
        top = ranked_stocks(listed)
        with ThreadPoolExecutor(max_workers=6) as pool:
            rows = list(pool.map(lambda r: signal_row(r, today), top.to_dict("records")))
        result = pd.DataFrame(rows).sort_values("rank")
        try:
            themes = fetch_themes()
        except Exception as exc:  # the page falls back to the KRX sector
            themes = {}
            debug["errors"].append(f"themes: {type(exc).__name__}: {exc}")
        result["theme"] = result["code"].map(lambda c: themes.get(str(c), ""))
        # label with the trading day the prices are from (a holiday run keeps the last session)
        trade_day = result["last_date"].dropna().mode()
        day = pd.Timestamp(trade_day.iloc[0]).date() if len(trade_day) else today
        result.insert(0, "date", day.isoformat())
        result["scanned_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        result.to_csv(OUT / f"kr_top100_{day:%Y%m%d}.csv", index=False, encoding="utf-8")
        result.to_csv(OUT / "kr_top100_latest.csv", index=False, encoding="utf-8")
        debug["rows"] = int(len(result))
        etf = etf_rows(listed, today)
        if not etf.empty:
            etf.insert(0, "date", day.isoformat())
            etf["scanned_at"] = result["scanned_at"].iloc[0]
            etf.to_csv(OUT / f"kr_etf30_{day:%Y%m%d}.csv", index=False, encoding="utf-8")
            etf.to_csv(OUT / "kr_etf30_latest.csv", index=False, encoding="utf-8")
            debug["etf_rows"] = int(len(etf))
            debug["etf_kinds"] = etf["kind"].value_counts().to_dict()
        debug["status_counts"] = result["status"].value_counts().to_dict()
    except Exception as exc:
        debug["errors"].append(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        (OUT / "kr_top100_debug.json").write_text(json.dumps(debug, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
