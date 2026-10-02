"""One-off probe: which Naver endpoints expose themes. Writes out/probe.json."""
import json, re, sys
from pathlib import Path
import requests
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15", "Referer": "https://m.stock.naver.com/"}
urls = [
    "https://m.stock.naver.com/api/stocks/theme?page=1&pageSize=20",
    "https://m.stock.naver.com/api/stocks/themes?page=1&pageSize=20",
    "https://m.stock.naver.com/api/stocks/theme/list?page=1&pageSize=20",
    "https://m.stock.naver.com/front-api/stocks/theme?page=1&pageSize=20",
    "https://stock.naver.com/api/domestic/market/theme?page=1&pageSize=20",
    "https://m.stock.naver.com/api/stock/005930/integration",
    "https://m.stock.naver.com/api/stock/005930/basic",
]
out = {}
for u in urls:
    try:
        r = requests.get(u, headers=H, timeout=15)
        out[u] = {"status": r.status_code, "head": r.text[:700]}
    except Exception as e:
        out[u] = {"error": str(e)}
# look inside the new theme page for API hints
try:
    html = requests.get("https://finance.naver.com/sise/theme.naver", headers=H, timeout=15).text
    out["hints"] = sorted(set(re.findall(r'(https?://[a-z.]*naver\.com/[a-zA-Z0-9/_\-.]*theme[a-zA-Z0-9/_\-.]*)', html)))[:30]
    out["no_hits"] = re.findall(r'.{80}themeNo.{120}', html)[:3] + re.findall(r'.{80}groupNo.{120}', html)[:3]
except Exception as e:
    out["hints_error"] = str(e)
Path(sys.argv[1]).mkdir(exist_ok=True)
Path(sys.argv[1], "probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
