"""One-off: today's buy candidates with representative themes under four rules."""
import io, json, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd, requests
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)", "Referer": "https://m.stock.naver.com/"}
csv = requests.get("https://raw.githubusercontent.com/jangjb1204-sys/us-stock-dashboard/kr-scans/kr_top100_latest.csv", timeout=15).text
d = pd.read_csv(io.StringIO(csv), dtype={"code": str})
c = d[(d.status == "ok") & (d.next_weight == 1.0) & (d.overheated.astype(str).str.lower() != "true")].copy()
c["_up"] = (c.next_weight > c.weight).astype(int)
c = c.sort_values(["_up", "to_full_pct"], ascending=[False, False])
groups = []
for page in range(1, 15):
    b = requests.get("https://m.stock.naver.com/api/stocks/theme", params={"page": page, "pageSize": 100}, headers=H, timeout=15).json().get("groups") or []
    groups += b
    if len(b) < 100: break
order = {g["name"]: i for i, g in enumerate(groups)}          # Naver order = today's change
size = {g["name"]: int(g.get("totalCount") or 0) for g in groups}
def members(g):
    try:
        s = requests.get(f"https://m.stock.naver.com/api/stocks/theme/{g['no']}", params={"page": 1, "pageSize": 100}, headers=H, timeout=15).json().get("stocks") or []
        return g["name"], [x.get("itemCode") for x in s]
    except Exception:
        return g["name"], []
by = {}
with ThreadPoolExecutor(4) as p:
    for name, codes in p.map(members, groups):
        for code in codes: by.setdefault(code, []).append(name)
short = lambda n: re.sub(r"\s*\(.*?\)", "", n).strip()
generic = re.compile(r"밸류업|S7|신규상장|스팩|지주사|대표주|우선주|코스피200|외국인|기관")
out = []
for r in c.itertuples():
    ts = by.get(r.code, [])
    pick = lambda key, keep=lambda n: True: [short(n) for n in sorted([t for t in ts if keep(t)], key=key)][:2]
    out.append({"name": r.name, "n_themes": len(ts),
        "A_today": pick(lambda n: order.get(n, 9999)),
        "B_broad": pick(lambda n: -size.get(n, 0)),
        "C_narrow": pick(lambda n: size.get(n, 0)),
        "D_broad_no_generic": pick(lambda n: -size.get(n, 0), lambda n: not generic.search(n)),
        "all": [short(n) for n in ts]})
Path(sys.argv[1]).mkdir(exist_ok=True)
Path(sys.argv[1], "theme_criteria.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
