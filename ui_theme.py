"""Shared look for every page of the app (US, Puddle, KOSPI/KOSDAQ).

Values mirror the US page's final design layer in main.py, so a page that
loads BASE_CSS looks like the US page. Each page still keeps its own CSS for
things only it has (calendar, signal feed, ...).

Also provides the top navigation, the page header, the footer, and html(),
which makes multi-line HTML safe to hand to st.markdown.
"""

from __future__ import annotations

from html import escape
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

# ── Tokens ─────────────────────────────────────────────────────────────────────
BG = "#05070B"
TEXT = "#F2F5F8"
MUTED = "rgba(255,255,255,0.48)"
FAINT = "rgba(255,255,255,0.36)"
LINE = "rgba(255,255,255,0.07)"
ACCENT = "#2F80FF"
GREEN = "#3FB950"
YELLOW = "#F0C35A"
RED = "#FF5A5F"
PLOT_BG = "#05070d"
# Tesla-style monochrome: meaning is carried by lightness, not hue. One accent
# (ACCENT) is kept for focus/selection. Allocation levels use these greys.
LEVEL_FULL = "#C9CED6"   # 100%
LEVEL_HALF = "#8A9099"   # 50%
LEVEL_NONE = "#3A4049"   # 0%
FONT_STACK = '-apple-system, BlinkMacSystemFont, "Inter", "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", "DM Sans", sans-serif'

PAGES = [
    ("us", "미국 시장"),
    ("puddle", "Puddle 스캐너"),
    ("korea", "코스피 · 코스닥"),
]
KST = ZoneInfo("Asia/Seoul")
KO_WEEKDAYS = "월화수목금토일"
THREADS_URL = "https://www.threads.net/@30s_tech_j"


def kdate(value) -> str:
    """A date as Koreans read it: 9/25(금)."""
    d = pd.Timestamp(value)
    return f"{d.month}/{d.day}({KO_WEEKDAYS[d.weekday()]})"


def kst_time(value, tz=None) -> str:
    """A timestamp shown in Korean time: 9/26(토) 09:17 KST. Naive values are read in `tz`."""
    try:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize(tz or KST)
        ts = ts.tz_convert(KST)
    except Exception:
        return ""
    return f"{kdate(ts)} {ts:%H:%M} KST"


def html(markup: str) -> str:
    """Flatten indented, multi-line HTML for st.markdown.

    Markdown ends an HTML block at a blank line and treats lines indented four
    or more spaces after one as a code block, which is how a card built from an
    indented f-string ended up printed as source. Stripping every line and
    dropping blank ones keeps the whole string one HTML block.
    """
    return "\n".join(line.strip() for line in markup.splitlines() if line.strip())


BASE_CSS = f"""
<style>
html, body, [class*="css"], .stApp {{
    font-family: {FONT_STACK} !important;
    background: radial-gradient(circle at top left, rgba(47,128,255,0.045), transparent 32%), {BG} !important;
    color: {TEXT} !important;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}}
.stApp::before {{ display: none !important; }}
#MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stHeader"], [data-testid="collapsedControl"], [data-testid="stSidebar"] {{ display: none !important; }}
.block-container {{
    max-width: 1180px;
    padding-top: 2.15rem !important;
    padding-left: 2.4rem !important;
    padding-right: 2.4rem !important;
    padding-bottom: 3rem !important;
}}
p, li, div[data-testid="stMarkdownContainer"] {{ letter-spacing: 0 !important; line-height: 1.55; }}
hr {{ border-color: rgba(255,255,255,0.055) !important; margin: 2.15rem 0 2.35rem !important; }}

/* labels */
.tj-label,
div[data-testid="stSelectbox"] label,
div[data-testid="stRadio"] label,
div[data-testid="stTextInput"] label {{
    color: rgba(255,255,255,0.46) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.035em !important;
}}
.tj-label {{ margin: 1.55rem 0 0.64rem; }}

/* inputs */
div[data-baseweb="select"] > div,
div[data-testid="stTextInput"] > div,
div[data-testid="stTextInput"] [data-baseweb="input"] {{
    min-height: 46px !important;
    border-radius: 12px !important;
    background: rgba(255,255,255,0.035) !important;
    border: 0 !important;
    box-shadow: none !important;
}}
div[data-testid="stTextInput"] input {{ font-weight: 500 !important; letter-spacing: 0 !important; color: {TEXT} !important; }}
div[data-testid="stTextInput"] input::placeholder {{ color: rgba(255,255,255,0.34) !important; }}

/* radio -> pills */
div[data-testid="stRadio"] div[role="radiogroup"] {{
    display: flex !important; flex-wrap: wrap; align-items: center; gap: 6px !important;
    width: fit-content; max-width: 100%; padding: 0 !important; background: transparent !important; border: 0;
}}
div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child {{ display: none !important; }}
/* Newer Streamlit wraps the input in a hidden <span>, so the dot is one level deeper. */
div[data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) {{ display: none !important; }}
div[data-testid="stRadio"] label[data-testid="stRadioOption"] > div {{ gap: 0 !important; }}
/* Pill text never breaks inside a pill (it went one letter per line on phones). */
div[data-testid="stRadio"] div[role="radiogroup"] > div {{ flex-shrink: 0; }}
div[data-testid="stRadio"] label[data-testid="stRadioOption"] p {{ white-space: nowrap !important; }}
div[data-testid="stRadio"] div[role="radiogroup"] label {{
    display: inline-flex !important; align-items: center !important; justify-content: center !important;
    min-height: 35px !important; height: 35px !important; padding: 0 12px !important; margin: 0 !important;
    border: 1px solid rgba(255,255,255,0.05) !important; border-radius: 999px !important;
    background: rgba(255,255,255,0.035) !important; box-shadow: none !important;
    text-transform: none !important; letter-spacing: 0 !important;
}}
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {{
    background: rgba(242,245,248,0.76) !important; border-color: rgba(242,245,248,0.54) !important;
}}
div[data-testid="stRadio"] div[role="radiogroup"] label p {{
    color: {TEXT} !important; font-size: 0.75rem !important; font-weight: 620 !important;
    line-height: 1 !important; margin: 0 !important; padding: 0 !important;
}}
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {{ color: {BG} !important; }}

/* tabs -> underline */
.stTabs [data-baseweb="tab-list"] {{
    background: transparent !important; border: 0 !important; box-shadow: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.065) !important; border-radius: 0 !important;
    padding: 0 !important; gap: 26px !important;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 0 !important; padding: 0 0 13px !important; background: transparent !important;
    color: {FAINT} !important; font-size: 0.92rem !important; font-weight: 520 !important; box-shadow: none !important;
}}
.stTabs [aria-selected="true"] {{
    color: rgba(255,255,255,0.96) !important; background: transparent !important;
    box-shadow: inset 0 -2px 0 rgba(242,245,248,0.9) !important;
}}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none !important; }}
.stTabs [data-baseweb="tab"] p {{ color: inherit !important; font-weight: inherit !important; }}
.stTabs [aria-selected="true"] p {{ font-weight: 640 !important; }}

/* buttons */
.stButton > button, div[data-testid="stDownloadButton"] button {{
    min-height: 38px !important; padding: 7px 13px !important; border-radius: 999px !important;
    background: rgba(255,255,255,0.035) !important; border: 1px solid rgba(255,255,255,0.075) !important;
    color: rgba(255,255,255,0.66) !important; box-shadow: none !important; transform: none !important;
}}
.stButton > button p, div[data-testid="stDownloadButton"] button p {{
    color: rgba(255,255,255,0.66) !important; font-size: 0.78rem !important; font-weight: 560 !important;
}}
.stButton > button:hover, div[data-testid="stDownloadButton"] button:hover {{
    background: rgba(255,255,255,0.065) !important; border-color: rgba(255,255,255,0.12) !important;
}}
.stButton > button:hover p, div[data-testid="stDownloadButton"] button:hover p {{ color: rgba(255,255,255,0.82) !important; }}
.stButton > button[kind="primary"] {{ background: rgba(242,245,248,0.76) !important; border-color: rgba(242,245,248,0.54) !important; }}
.stButton > button[kind="primary"] p {{ color: {BG} !important; }}

/* expander */
div[data-testid="stExpander"] details, div[data-testid="stExpander"] details > div {{
    background: transparent !important; border-color: transparent !important; box-shadow: none !important;
}}
div[data-testid="stExpander"] details summary {{
    background: transparent !important; border: 0 !important; border-bottom: 1px solid {LINE} !important;
    border-radius: 0 !important; padding-left: 0 !important; padding-right: 0 !important;
}}
div[data-testid="stExpander"] details summary p {{ color: rgba(255,255,255,0.82) !important; }}
.stSpinner > div {{ border-top-color: {ACCENT} !important; }}
div[data-testid="stPlotlyChart"] .modebar {{ display: none !important; }}

/* navigation */
.tj-nav {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 1.6rem; }}
.tj-nav a {{
    display: inline-flex; align-items: center; height: 32px; padding: 0 13px; border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.05); background: rgba(255,255,255,0.035);
    color: rgba(255,255,255,0.62) !important; font-size: 0.78rem; font-weight: 600; text-decoration: none !important;
    white-space: nowrap; transition: background .15s ease, color .15s ease;
}}
.tj-nav a:hover {{ background: rgba(255,255,255,0.07); color: {TEXT} !important; }}
.tj-nav a.active {{ background: rgba(242,245,248,0.76); border-color: rgba(242,245,248,0.54); color: {BG} !important; }}

/* page header */
.tj-hero {{ display: flex; justify-content: space-between; align-items: center; gap: 20px; margin: 0 0 2.15rem; }}
.tj-title-row {{ display: flex; align-items: center; gap: 12px; }}
.tj-hero h1 {{
    margin: 0 !important; padding: 0 !important; font-size: 39px !important; line-height: 1.08 !important;
    font-weight: 680 !important; letter-spacing: -0.02em !important; color: {TEXT} !important; text-shadow: none !important;
}}
.tj-hero h1 a {{ color: inherit !important; text-decoration: none !important; }}
.tj-dot {{ width: 8px; height: 8px; border-radius: 999px; flex: 0 0 auto; background: rgba(255,255,255,0.32); }}
.tj-dot.open, .tj-dot.live {{ background: {TEXT}; }}
.tj-meta {{ margin-top: 0.42rem; color: rgba(255,255,255,0.52); font-size: 0.78rem; font-weight: 500; }}
.tj-hero.compact {{ margin: -0.4rem 0 1.9rem; }}
.tj-hero.compact .tj-meta {{ margin-top: 0; display: flex; align-items: center; flex-wrap: wrap; }}
.tj-hero.compact .tj-dot {{ width: 6px; height: 6px; margin-right: 8px; }}
.tj-meta .k {{ color: {FAINT}; text-transform: uppercase; letter-spacing: 0.04em; margin-right: 6px; }}
.tj-meta .sep {{ margin: 0 8px; color: rgba(255,255,255,0.22); }}
.tj-hero-right {{ display: flex; align-items: center; gap: 8px; color: rgba(255,255,255,0.52); font-size: 0.78rem; white-space: nowrap; }}
.tj-hero-right strong {{ color: {TEXT}; font-weight: 650; }}
.tj-hero-right .tj-dot {{ width: 6px; height: 6px; background: rgba(255,255,255,0.5); }}

/* focus title: eyebrow + big name */
.tj-focus {{ margin: 2.05rem 0 0.95rem; }}
.tj-focus .eyebrow {{ color: rgba(255,255,255,0.46); font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.035em; }}
.tj-focus .name {{ margin-top: .35rem; font-size: 42px; font-weight: 700; letter-spacing: -0.024em; color: {TEXT}; line-height: 1.1; }}
.tj-focus .ticker {{ margin-left: 0.55rem; color: rgba(255,255,255,0.46); font-size: 1.02rem; font-weight: 500; }}

/* stat rows */
.tj-stats {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); column-gap: 44px; row-gap: 22px; }}
.tj-stat {{ padding: 24px 0 0; border-top: 1px solid {LINE}; min-width: 0; }}
.tj-stat .label {{ color: {MUTED}; font-size: 12px; font-weight: 560; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 7px; }}
.tj-stat .value {{ font-variant-numeric: tabular-nums; color: {TEXT}; font-size: 1.26rem; font-weight: 620; letter-spacing: -0.01em; }}
.tj-stat .note {{ margin-top: 5px; font-size: 0.82rem; color: rgba(255,255,255,0.56); line-height: 1.4; }}
.tj-green, .tj-yellow, .tj-red, .tj-blue {{ color: {TEXT} !important; }}

/* chips & notes */
.tj-chip {{
    display: inline-flex; align-items: center; gap: 6px; height: 26px; padding: 0 10px; border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.09); background: transparent;
    color: rgba(255,255,255,0.62); font-size: 0.76rem; font-weight: 560; white-space: nowrap;
}}
.tj-chip.green, .tj-chip.yellow, .tj-chip.red, .tj-chip.blue, .tj-chip.on {{ color: {TEXT}; border-color: rgba(255,255,255,0.22); }}
.tj-note {{
    margin: 0 0 1rem; padding: 2px 0 2px 12px; border-left: 2px solid rgba(255,255,255,0.28); background: transparent;
    color: rgba(255,255,255,0.72); font-size: 0.86rem; line-height: 1.55;
}}
.tj-note.warn, .tj-note.ok {{ border-left-color: rgba(255,255,255,0.72); color: {TEXT}; }}
.tj-note b {{ color: {TEXT}; }}

/* verdict: the page's "so what" as a row of chips */
.tj-verdict {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:4px 0; margin:.2rem 0 1.6rem; color:rgba(255,255,255,0.56); font-size:.86rem; }}
.tj-verdict .lead {{ color:{MUTED}; font-size:12px; font-weight:560; letter-spacing:.04em; margin-right:12px; }}
.tj-verdict .item + .item::before {{ content:"·"; margin:0 9px; color:rgba(255,255,255,0.24); }}
.tj-verdict .item.em {{ color:{TEXT}; font-weight:600; }}
@media (max-width:640px) {{
    .tj-verdict {{ flex-direction:column; align-items:flex-start; gap:4px; }}
    .tj-verdict .lead {{ margin-bottom:2px; }}
    .tj-verdict .item + .item::before {{ content:none; }}
}}

/* label / value lines (short explanations) */
.tj-lines {{ display:grid; grid-template-columns:max-content minmax(0,1fr); column-gap:20px; row-gap:9px; margin:1.3rem 0 1.6rem; font-size:.9rem; line-height:1.5; }}
.tj-lines .k {{ color:{MUTED}; font-size:12px; font-weight:560; letter-spacing:.04em; padding-top:2px; white-space:nowrap; }}
.tj-lines .v {{ color:rgba(255,255,255,0.80); min-width:0; }}
.tj-lines .v b {{ color:{TEXT}; font-weight:640; }}
@media (max-width:640px) {{ .tj-lines {{ grid-template-columns:1fr; row-gap:2px; }} .tj-lines .v {{ margin-bottom:8px; }} }}

/* tables */
.tj-table-wrap {{ overflow-x: auto; margin-top: .4rem; }}
.tj-table {{ width: 100%; border-collapse: collapse; min-width: 620px; font-variant-numeric: tabular-nums; }}
.tj-table th {{
    background: #101722; color: rgba(255,255,255,0.50); font-size: 0.76rem; font-weight: 560; text-align: left;
    padding: 11px 12px; box-shadow: 0 1px 0 {LINE};
}}
.tj-table td {{ background: #080D14; color: rgba(255,255,255,0.82); font-size: 0.86rem; font-weight: 450; padding: 11px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); }}
.tj-table tr:nth-child(even) td {{ background: #0A111A; }}
.tj-table tr:hover td {{ background: #0D1A2A; }}
.tj-table tr.best td {{ background: rgba(47,128,255,0.10); }}
.tj-caption {{ color: rgba(255,255,255,0.44); font-size: 0.8rem; line-height: 1.55; margin-top: .8rem; }}

/* footer */
.tj-footer {{
    margin: 3.2rem 0 0.2rem; padding-top: 1.2rem; border-top: 1px solid rgba(255,255,255,0.045);
    color: rgba(255,255,255,0.34); font-size: 0.78rem; font-weight: 500;
}}
.tj-footer .sep {{ margin: 0 8px; color: rgba(255,255,255,0.22); }}
.tj-footer a {{ color: rgba(255,255,255,0.48) !important; text-decoration: none !important; }}
.tj-footer a:hover {{ color: rgba(255,255,255,0.72) !important; }}

@media (max-width: 900px) {{ .tj-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 24px; }} }}
@media (max-width: 640px) {{
    .block-container {{ padding-top: 1.3rem !important; padding-left: 0.85rem !important; padding-right: 0.85rem !important; }}
    .tj-nav {{ margin-bottom: 1.2rem; }}
    .tj-hero {{ flex-direction: column; align-items: flex-start; gap: 12px; margin-bottom: 1.6rem; }}
    .tj-hero h1 {{ font-size: 29px !important; line-height: 1.05 !important; }}
    .tj-focus .name {{ font-size: 30px; }}
    .tj-stats {{ column-gap: 18px; }}
}}
</style>
"""


def nav_html(active: str) -> str:
    items = "".join(
        f'<a class="{"active" if key == active else ""}" href="?dashboard={key}" target="_self">{escape(label)}</a>'
        for key, label in PAGES
    )
    return f'<nav class="tj-nav">{items}</nav>'


def hero_html(title: str, updated: str | None = None, dot: str = "live", right: str = "", extra_meta: str = "",
              self_key: str = "us") -> str:
    """Page header: just the data timestamp. The page name is already the
    active nav pill, so no big title repeats it (`title` stays for callers
    and the browser tab). `right` and `extra_meta` are trusted HTML."""
    meta = ""
    if updated:
        meta = f'<span class="k">기준</span>{escape(updated)}'
    if extra_meta:
        meta += (f'<span class="sep">·</span>' if meta else "") + extra_meta
    return html(f"""
        <div class="tj-hero compact">
          <div class="tj-meta"><span class="tj-dot {escape(dot)}"></span>{meta}</div>
          <div class="tj-hero-right">{right}</div>
        </div>
    """)


def viewers_html(count: int) -> str:
    return f'<span class="tj-dot"></span><span>지금 보는 중 <strong>{count:,}</strong></span>'


DISCLAIMER = "과거 데이터로 규칙을 계산한 참고 자료이며 투자 권유가 아닙니다."


def footer_html() -> str:
    return (f'<div class="tj-footer">{DISCLAIMER}<span class="sep">·</span>'
            f'by <a href="{THREADS_URL}" target="_blank" rel="noopener noreferrer">30s_tech_j</a></div>')


def header(st, active: str, title: str, **hero_kwargs) -> None:
    """Base CSS + navigation + page header, for pages that render them once."""
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    st.markdown(nav_html(active), unsafe_allow_html=True)
    st.markdown(hero_html(title, self_key=active, **hero_kwargs), unsafe_allow_html=True)


# Plotly layout pieces shared by every chart
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=PLOT_BG,
    font={"family": "DM Sans, -apple-system, BlinkMacSystemFont, Inter, Pretendard, sans-serif", "color": "#d7dce5", "size": 11},
)
X_GRID = dict(showgrid=True, gridcolor="rgba(255,255,255,0.055)", zeroline=False)
Y_GRID = dict(showgrid=True, gridcolor="rgba(255,255,255,0.075)", zeroline=False)
