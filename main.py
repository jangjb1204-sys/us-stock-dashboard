import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from html import escape
import time
import uuid
from zoneinfo import ZoneInfo

from stock_analyzer import (
    TICKER_CONFIGS,
    fetch_batch_stock_data,
    fetch_common_market_data,
    process_stock_frame,
    process_stock_data,
)

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="US Market Signals",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 스타일 ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'DM Sans', sans-serif !important;
        background:
            linear-gradient(118deg, rgba(182,221,255,0.08) 0%, rgba(182,221,255,0) 34%),
            linear-gradient(212deg, rgba(0,117,255,0.14) 0%, rgba(0,117,255,0) 42%),
            linear-gradient(180deg, #091b31 0%, #061323 42%, #020711 100%) !important;
        color: #f5f5f7 !important;
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        background:
            linear-gradient(112deg, transparent 0%, rgba(235,247,255,0.13) 18%, transparent 36%),
            linear-gradient(75deg, transparent 52%, rgba(86,154,255,0.10) 72%, transparent 90%);
        opacity: 0.72;
        mix-blend-mode: screen;
    }
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    #MainMenu,
    header,
    footer,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }
    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1360px;
        position: relative;
        z-index: 1;
    }
    .app-hero {
        position: relative;
        overflow: hidden;
        margin: 0.2rem 0 1.05rem;
        padding: 1.22rem 1.32rem 1.18rem;
        border: 1px solid rgba(190,220,255,0.24);
        border-radius: 30px;
        background:
            linear-gradient(142deg, rgba(238,248,255,0.21), rgba(117,181,255,0.07) 38%, rgba(255,255,255,0.035) 70%),
            rgba(8,28,50,0.62);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.34),
            inset 0 -1px 0 rgba(255,255,255,0.08),
            0 22px 70px rgba(0,0,0,0.32),
            0 0 0 1px rgba(255,255,255,0.035);
        backdrop-filter: blur(34px) saturate(1.65);
        -webkit-backdrop-filter: blur(34px) saturate(1.65);
    }
    .app-hero::before {
        content: "";
        position: absolute;
        left: 22px;
        right: 22px;
        top: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.58), transparent);
        opacity: 0.95;
    }
    .app-hero::after {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background:
            linear-gradient(120deg, rgba(255,255,255,0.24), transparent 30%, transparent 74%, rgba(255,255,255,0.08)),
            linear-gradient(180deg, rgba(255,255,255,0.07), transparent 42%);
        opacity: 0.66;
    }
    .app-hero h1 {
        position: relative;
        z-index: 1;
        margin: 0;
        font-size: 2.42rem !important;
        line-height: 1.08;
        font-weight: 760 !important;
        letter-spacing: 0;
        color: #f7fbff !important;
        text-shadow: 0 12px 34px rgba(0,0,0,0.28);
    }
    .hero-title {
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        gap: 13px;
        flex-wrap: wrap;
    }
    .market-status-dot,
    .viewer-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        flex: 0 0 auto;
    }
    .market-status-dot.open {
        background: #63f29d;
        box-shadow:
            0 0 0 1px rgba(255,255,255,0.30),
            0 0 10px rgba(99,242,157,0.42),
            0 0 22px rgba(99,242,157,0.24);
        animation: elegantPulseGreen 2.8s ease-in-out infinite;
    }
    .market-status-dot.closed {
        background: #8e8e93;
        box-shadow:
            0 0 0 1px rgba(255,255,255,0.18),
            0 0 10px rgba(142,142,147,0.18);
        opacity: 0.72;
    }
    .hero-row {
        position: relative;
        z-index: 1;
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 16px;
    }
    .viewer-pill {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 10px 15px;
        border: 1px solid rgba(190,220,255,0.27);
        border-radius: 999px;
        background:
            linear-gradient(135deg, rgba(231,246,255,0.17), rgba(255,255,255,0.045)),
            rgba(7,24,43,0.58);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.24),
            0 14px 38px rgba(0,0,0,0.18);
        color: rgba(226,240,255,0.72);
        font-size: 0.82rem;
        white-space: nowrap;
        backdrop-filter: blur(22px) saturate(1.4);
        -webkit-backdrop-filter: blur(22px) saturate(1.4);
    }
    .viewer-pill strong {
        color: #9cccff;
        font-weight: 750;
    }
    .viewer-dot {
        background: #64a8ff;
        box-shadow:
            0 0 0 1px rgba(255,255,255,0.30),
            0 0 10px rgba(100,168,255,0.44),
            0 0 22px rgba(100,168,255,0.24);
        animation: elegantPulseBlue 3s ease-in-out infinite;
    }
    @keyframes elegantPulseGreen {
        0%, 100% { opacity: 0.70; filter: saturate(0.95); box-shadow: 0 0 0 1px rgba(255,255,255,0.24), 0 0 8px rgba(99,242,157,0.26), 0 0 18px rgba(99,242,157,0.12); }
        50% { opacity: 1; filter: saturate(1.18); box-shadow: 0 0 0 1px rgba(255,255,255,0.36), 0 0 13px rgba(99,242,157,0.54), 0 0 28px rgba(99,242,157,0.28); }
    }
    @keyframes elegantPulseBlue {
        0%, 100% { opacity: 0.72; filter: saturate(0.96); box-shadow: 0 0 0 1px rgba(255,255,255,0.24), 0 0 8px rgba(100,168,255,0.28), 0 0 18px rgba(100,168,255,0.12); }
        50% { opacity: 1; filter: saturate(1.16); box-shadow: 0 0 0 1px rgba(255,255,255,0.36), 0 0 13px rgba(100,168,255,0.56), 0 0 28px rgba(100,168,255,0.28); }
    }
    .app-hero p {
        position: relative;
        z-index: 1;
        margin: 0.45rem 0 0;
        color: #8e8e93;
        font-size: 0.88rem;
    }
    .creator-mark {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        margin-top: 0.62rem;
        padding: 6px 11px;
        border: 1px solid rgba(190,220,255,0.24);
        border-radius: 999px;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.13), rgba(255,255,255,0.035)),
            rgba(10,132,255,0.10);
        color: #b9ddff;
        font-family: 'DM Mono', monospace;
        font-size: 0.76rem;
        font-weight: 500;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.18);
        text-decoration: none;
        transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
    }
    .creator-mark:hover {
        background:
            linear-gradient(135deg, rgba(255,255,255,0.18), rgba(255,255,255,0.055)),
            rgba(10,132,255,0.16);
        border-color: rgba(207,228,255,0.42);
        transform: translateY(-1px);
    }
    .creator-mark::before {
        content: "by";
        color: rgba(226,240,255,0.48);
        font-family: 'DM Sans', sans-serif;
        font-size: 0.68rem;
        font-weight: 700;
    }
    .section-label {
        color: rgba(207,228,255,0.64);
        font-size: 0.8rem;
        font-weight: 700;
        margin: 1.2rem 0 0.45rem;
    }
    .focus-title {
        min-height: 76px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 0 0 0 0.2rem;
    }
    .focus-title .eyebrow {
        color: rgba(207,228,255,0.58);
        font-size: 0.8rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .focus-title .name {
        color: #f7fbff;
        font-size: 1.94rem;
        line-height: 1.05;
        font-weight: 750;
    }
    .focus-title .ticker {
        display: inline-block;
        margin-left: 0.55rem;
        padding: 0.16rem 0.52rem;
        border: 1px solid rgba(190,220,255,0.22);
        border-radius: 13px;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.20), rgba(10,132,255,0.16)),
            rgba(7,24,43,0.42);
        color: #c9e7ff;
        font-size: 1.06rem;
        font-family: 'DM Mono', monospace;
        font-weight: 500;
        vertical-align: 0.12rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.20);
    }
    .signal-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin: 0.7rem 0 1.1rem;
    }
    .signal-card {
        position: relative;
        overflow: hidden;
        min-height: 124px;
        padding: 16px 17px;
        border: 1px solid rgba(190,220,255,0.18);
        border-radius: 26px;
        background:
            linear-gradient(145deg, rgba(241,248,255,0.16), rgba(255,255,255,0.045) 48%, rgba(117,181,255,0.035)),
            rgba(7,23,42,0.52);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.28),
            inset 0 -1px 0 rgba(255,255,255,0.07),
            0 18px 58px rgba(0,0,0,0.25);
        backdrop-filter: blur(32px) saturate(1.58);
        -webkit-backdrop-filter: blur(32px) saturate(1.58);
    }
    .signal-card::after {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background:
            linear-gradient(118deg, rgba(255,255,255,0.20), transparent 34%),
            linear-gradient(180deg, color-mix(in srgb, var(--accent) 15%, transparent), transparent 58%);
        opacity: 0.72;
    }
    .signal-title {
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        gap: 8px;
        color: #f7fbff;
        font-size: 1.08rem;
        font-weight: 700;
        margin-bottom: 11px;
    }
    .signal-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: var(--accent);
        box-shadow: 0 0 18px color-mix(in srgb, var(--accent) 55%, transparent);
    }
    .signal-item {
        position: relative;
        z-index: 1;
        display: flex;
        justify-content: space-between;
        gap: 12px;
        padding: 7px 0;
        border-top: 1px solid rgba(255,255,255,0.08);
        color: rgba(235,244,255,0.86);
        font-size: 0.84rem;
    }
    .signal-item:first-of-type { border-top: none; }
    .signal-date {
        color: rgba(207,228,255,0.56);
        white-space: nowrap;
        font-family: 'DM Mono', monospace;
        font-size: 0.76rem;
    }
    .signal-empty {
        position: relative;
        z-index: 1;
        padding-top: 14px;
        color: rgba(207,228,255,0.54);
        font-size: 0.8rem;
    }
    .risk-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin: 0.95rem 0 1.2rem;
    }
    .risk-card {
        position: relative;
        overflow: hidden;
        min-height: 96px;
        padding: 15px 16px;
        border: 1px solid rgba(190,220,255,0.17);
        border-radius: 24px;
        background:
            linear-gradient(145deg, rgba(241,248,255,0.14), rgba(255,255,255,0.04) 54%, rgba(117,181,255,0.03)),
            rgba(7,23,42,0.52);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.24),
            inset 0 -1px 0 rgba(255,255,255,0.05),
            0 18px 54px rgba(0,0,0,0.22);
        backdrop-filter: blur(24px) saturate(1.42);
        -webkit-backdrop-filter: blur(24px) saturate(1.42);
    }
    .risk-card::after {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background:
            linear-gradient(120deg, rgba(255,255,255,0.15), transparent 38%),
            linear-gradient(180deg, color-mix(in srgb, var(--accent) 18%, transparent), transparent 62%);
        opacity: 0.7;
    }
    .risk-top, .risk-main, .risk-caption {
        position: relative;
        z-index: 1;
    }
    .risk-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        color: #8e8e93;
        font-size: 0.76rem;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .risk-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 8px;
        border: 1px solid color-mix(in srgb, var(--accent) 44%, rgba(255,255,255,0.15));
        border-radius: 999px;
        color: var(--accent);
        background: color-mix(in srgb, var(--accent) 13%, transparent);
        font-size: 0.72rem;
        font-weight: 700;
        white-space: nowrap;
    }
    .risk-badge::before {
        content: "";
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: var(--accent);
        box-shadow: 0 0 14px color-mix(in srgb, var(--accent) 70%, transparent);
    }
    .risk-main {
        color: #f5f5f7;
        font-family: 'DM Mono', monospace;
        font-size: 1.34rem;
        font-weight: 500;
        line-height: 1.1;
    }
    .risk-caption {
        margin-top: 7px;
        color: #9b9ba1;
        font-size: 0.78rem;
    }

    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background: #0b0b0d !important;
        border-right: 1px solid rgba(255,255,255,0.08) !important;
    }
    section[data-testid="stSidebar"] * { font-family: 'DM Sans', sans-serif !important; }
    section[data-testid="stSidebar"] h2 {
        color: #f5f5f7 !important;
        font-size: 1rem !important;
        font-weight: 650 !important;
        letter-spacing: 0;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] small {
        color: #8e8e93 !important;
        font-size: 0.82rem !important;
    }

    /* 상단 컨트롤 */
    div[data-testid="stSelectbox"] label,
    div[data-testid="stRadio"] label,
    div[data-testid="stTextInput"] label {
        color: rgba(207,228,255,0.64) !important;
        font-size: 0.76rem !important;
        font-weight: 600 !important;
        letter-spacing: 0 !important;
    }
    div[data-baseweb="select"] > div {
        background:
            linear-gradient(135deg, rgba(241,248,255,0.15), rgba(255,255,255,0.04)),
            rgba(7,23,42,0.56) !important;
        border: 1px solid rgba(190,220,255,0.20) !important;
        border-radius: 18px !important;
        min-height: 48px !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), 0 16px 42px rgba(0,0,0,0.18) !important;
        backdrop-filter: blur(24px) saturate(1.45);
        -webkit-backdrop-filter: blur(24px) saturate(1.45);
    }
    div[data-baseweb="select"] span {
        color: #f5f5f7 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stTextInput"] > div,
    div[data-testid="stTextInput"] [data-baseweb="input"] {
        min-height: 48px !important;
        border-radius: 18px !important;
        overflow: hidden !important;
        background:
            linear-gradient(135deg, rgba(241,248,255,0.12), rgba(255,255,255,0.035)),
            rgba(9,28,50,0.72) !important;
        border: 1px solid rgba(190,220,255,0.28) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.18),
            inset 0 -1px 0 rgba(255,255,255,0.06),
            0 16px 42px rgba(0,0,0,0.14) !important;
        backdrop-filter: blur(24px) saturate(1.45);
        -webkit-backdrop-filter: blur(24px) saturate(1.45);
    }
    div[data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
        border-color: rgba(207,228,255,0.55) !important;
        outline: none !important;
    }
    div[data-testid="stTextInput"] [data-baseweb="input"] * {
        outline: none !important;
        box-shadow: none !important;
    }
    div[data-testid="stTextInput"] input {
        display: block !important;
        width: 100% !important;
        height: 48px !important;
        min-height: 48px !important;
        padding: 0 16px !important;
        border: 0 !important;
        border-radius: 18px !important;
        outline: none !important;
        background: transparent !important;
        color: #f5f5f7 !important;
        font-weight: 600 !important;
        box-shadow: none !important;
        backdrop-filter: blur(24px) saturate(1.45);
        -webkit-backdrop-filter: blur(24px) saturate(1.45);
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: rgba(207,228,255,0.55) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.22),
            0 0 0 1px rgba(156,204,255,0.18),
            0 16px 42px rgba(0,0,0,0.14) !important;
    }
    div[data-testid="stTextInput"] input::placeholder {
        color: rgba(207,228,255,0.42) !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex;
        flex-wrap: wrap;
        gap: 9px;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        background:
            linear-gradient(135deg, rgba(241,248,255,0.13), rgba(255,255,255,0.035)),
            rgba(7,23,42,0.50);
        border: 1px solid rgba(190,220,255,0.18);
        border-radius: 999px;
        min-height: 40px;
        padding: 8px 14px;
        margin: 0;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.15), 0 12px 28px rgba(0,0,0,0.14);
        backdrop-filter: blur(18px) saturate(1.28);
        -webkit-backdrop-filter: blur(18px) saturate(1.28);
        transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
        background:
            linear-gradient(145deg, rgba(232,246,255,0.96), rgba(156,204,255,0.74));
        border-color: rgba(231,246,255,0.78);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.92), 0 18px 42px rgba(55,144,255,0.20);
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover { transform: translateY(-1px); }
    div[data-testid="stRadio"] div[role="radiogroup"] label p {
        color: #f5f5f7 !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
        color: #071323 !important;
    }

    /* 메트릭 카드 */
    div[data-testid="metric-container"] {
        background:
            linear-gradient(145deg, rgba(241,248,255,0.14), rgba(255,255,255,0.04) 54%, rgba(117,181,255,0.03)),
            rgba(7,23,42,0.52);
        border: 1px solid rgba(190,220,255,0.17);
        border-radius: 24px;
        padding: 17px 18px;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.24),
            inset 0 -1px 0 rgba(255,255,255,0.05),
            0 18px 54px rgba(0,0,0,0.22);
        backdrop-filter: blur(28px) saturate(1.5);
        -webkit-backdrop-filter: blur(28px) saturate(1.5);
        transition: border-color 0.15s ease, background 0.15s ease, transform 0.15s ease;
    }
    div[data-testid="metric-container"]:hover {
        background:
            linear-gradient(145deg, rgba(255,255,255,0.17), rgba(255,255,255,0.045)),
            rgba(10,31,56,0.62);
        border-color: rgba(190,220,255,0.28);
        transform: translateY(-1px);
    }
    div[data-testid="metric-container"] label {
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0 !important;
        color: rgba(207,228,255,0.60) !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-family: 'DM Mono', monospace !important;
        font-size: 1.26rem !important;
        font-weight: 500 !important;
        color: #f7fbff !important;
        letter-spacing: 0;
    }
    div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-size: 0.74rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em;
    }

    /* 탭 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        width: fit-content;
        max-width: 100%;
        background:
            linear-gradient(135deg, rgba(241,248,255,0.12), rgba(255,255,255,0.035)),
            rgba(7,23,42,0.48);
        border: 1px solid rgba(190,220,255,0.16);
        border-radius: 999px;
        padding: 5px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 16px 42px rgba(0,0,0,0.16);
        backdrop-filter: blur(22px) saturate(1.4);
        -webkit-backdrop-filter: blur(22px) saturate(1.4);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 999px;
        color: #8e8e93;
        font-weight: 600;
        font-size: 0.82rem;
        letter-spacing: 0;
        padding: 7px 14px;
        border: 0;
        transition: color 0.15s ease, background 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover { color: #f5f5f7; background: rgba(255,255,255,0.05); }
    .stTabs [data-baseweb="tab"] p {
        color: inherit !important;
        font-weight: 600 !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(145deg, rgba(232,246,255,0.96), rgba(156,204,255,0.74)) !important;
        color: #071323 !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.85), 0 10px 28px rgba(55,144,255,0.18);
    }
    .stTabs [aria-selected="true"] p {
        color: #071323 !important;
    }

    /* 헤딩 */
    h1 {
        color: #f5f5f7 !important;
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        letter-spacing: 0;
    }
    h2 { color: #f5f5f7 !important; font-weight: 700 !important; letter-spacing: 0; }
    h3 {
        color: #f5f5f7 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        letter-spacing: 0;
    }
    p, li { color: #9b9ba1; font-size: 0.84rem; }

    /* 버튼 */
    .stButton > button {
        background:
            linear-gradient(135deg, rgba(241,248,255,0.13), rgba(255,255,255,0.035)),
            rgba(7,23,42,0.50);
        color: #dff0ff;
        border: 1px solid rgba(190,220,255,0.18);
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.82rem;
        letter-spacing: 0;
        min-height: 40px;
        padding: 8px 14px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.15), 0 12px 28px rgba(0,0,0,0.14);
        backdrop-filter: blur(18px) saturate(1.28);
        -webkit-backdrop-filter: blur(18px) saturate(1.28);
        transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
    }
    .stButton > button p { color: #d9ecff !important; }
    .stButton > button:hover {
        background:
            linear-gradient(145deg, rgba(232,246,255,0.96), rgba(156,204,255,0.74));
        border-color: rgba(231,246,255,0.78);
        transform: translateY(-1px);
    }
    .stButton > button:hover p { color: #071323 !important; }

    /* 다운로드 버튼 */
    .stDownloadButton > button {
        background:
            linear-gradient(135deg, rgba(241,248,255,0.13), rgba(255,255,255,0.035)),
            rgba(7,23,42,0.50);
        color: #b9ddff;
        border: 1px solid rgba(190,220,255,0.18);
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.82rem;
        min-height: 40px;
        padding: 8px 14px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.15), 0 12px 28px rgba(0,0,0,0.14);
        transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
    }
    .stDownloadButton > button p { color: #b9ddff !important; }
    .stDownloadButton > button:hover {
        background: linear-gradient(145deg, rgba(232,246,255,0.96), rgba(156,204,255,0.74));
        border-color: rgba(231,246,255,0.78);
        transform: translateY(-1px);
    }
    .stDownloadButton > button:hover p { color: #071323 !important; }

    /* 스피너 */
    .stSpinner > div { border-top-color: #0a84ff !important; }

    /* expander */
    details {
        border: 1px solid rgba(190,220,255,0.17) !important;
        border-radius: 26px !important;
        background:
            linear-gradient(145deg, rgba(241,248,255,0.14), rgba(255,255,255,0.04) 48%, rgba(117,181,255,0.03)),
            rgba(7,23,42,0.52) !important;
        padding: 4px 6px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.24),
            inset 0 -1px 0 rgba(255,255,255,0.05),
            0 22px 70px rgba(0,0,0,0.28);
        backdrop-filter: blur(28px) saturate(1.45);
        -webkit-backdrop-filter: blur(28px) saturate(1.45);
    }
    details summary {
        color: #eaf5ff !important;
        font-weight: 600;
        font-size: 0.84rem;
        margin: 0 !important;
        padding: 12px 14px !important;
        border-radius: 21px !important;
        border: 1px solid rgba(190,220,255,0.10) !important;
        background:
            linear-gradient(140deg, rgba(213,235,255,0.13), rgba(91,151,224,0.06)),
            rgba(12,34,61,0.54) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.14),
            inset 0 -1px 0 rgba(255,255,255,0.035) !important;
    }
    details[open] summary,
    div[data-testid="stExpander"] details[open] summary,
    div[data-testid="stExpander"] details[open] summary:hover {
        background:
            linear-gradient(140deg, rgba(213,235,255,0.18), rgba(83,145,222,0.08) 55%, rgba(255,255,255,0.035)),
            rgba(12,34,61,0.68) !important;
        border-color: rgba(190,220,255,0.18) !important;
        color: #f1f8ff !important;
    }
    details summary::marker {
        color: #c9e7ff !important;
    }
    div[data-testid="stExpander"] > details > summary > div {
        color: #eaf5ff !important;
    }
    details summary p,
    details summary span {
        color: #eaf5ff !important;
        font-weight: 650 !important;
    }

    /* code 배지 */
    code {
        background: rgba(10,132,255,0.14) !important;
        color: #9cccff !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.78em !important;
        border-radius: 8px !important;
        padding: 2px 8px !important;
        border: 1px solid rgba(10,132,255,0.28) !important;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(190,220,255,0.16);
        border-radius: 22px;
        overflow: hidden;
        background: rgba(8,25,45,0.72);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 18px 58px rgba(0,0,0,0.18);
        backdrop-filter: blur(20px) saturate(1.35);
        -webkit-backdrop-filter: blur(20px) saturate(1.35);
    }
    div[data-testid="stPlotlyChart"] {
        min-height: 460px;
    }
    div[data-testid="stPlotlyChart"] .js-plotly-plot,
    div[data-testid="stPlotlyChart"] .plotly,
    div[data-testid="stPlotlyChart"] .main-svg {
        min-height: 460px;
    }
    .glass-table-wrap {
        width: 100%;
        max-height: 520px;
        overflow: auto;
        border: 1px solid rgba(190,220,255,0.17);
        border-radius: 22px;
        background:
            linear-gradient(145deg, rgba(241,248,255,0.11), rgba(255,255,255,0.025)),
            rgba(8,25,45,0.66);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.16),
            0 18px 58px rgba(0,0,0,0.18);
        backdrop-filter: blur(22px) saturate(1.38);
        -webkit-backdrop-filter: blur(22px) saturate(1.38);
    }
    .glass-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        color: #f5f5f7;
        font-size: 0.86rem;
    }
    .glass-table th {
        position: sticky;
        top: 0;
        z-index: 1;
        padding: 12px 13px;
        text-align: left;
        color: rgba(226,240,255,0.68);
        background:
            linear-gradient(180deg, rgba(39,67,104,0.95), rgba(25,48,78,0.95));
        border-bottom: 1px solid rgba(190,220,255,0.14);
        font-weight: 700;
        white-space: nowrap;
    }
    .glass-table td {
        padding: 11px 13px;
        border-bottom: 1px solid rgba(190,220,255,0.08);
        background: rgba(10,28,50,0.54);
        white-space: nowrap;
    }
    .glass-table tr:nth-child(even) td {
        background: rgba(15,38,66,0.58);
    }
    .glass-table tr:hover td {
        background: rgba(31,74,118,0.70);
    }
    .glass-table tr.signal-row td {
        background: rgba(255,204,102,0.13);
    }
    .glass-table tr.sigma-row td {
        background: rgba(94,228,255,0.11);
    }
    .glass-table td.num {
        text-align: right;
        font-family: 'DM Mono', monospace;
    }
    .glass-table td.pos { color: #78b7ff; font-weight: 700; }
    .glass-table td.neg { color: #ff7b72; font-weight: 700; }
    .glass-table td.hot { color: #ff7b72; font-weight: 700; }
    .glass-table td.cool { color: #78b7ff; font-weight: 700; }

    /* progress bar */
    .stProgress > div > div { background: #0a84ff !important; border-radius: 4px; }

    /* 구분선 */
    hr { border-color: rgba(255,255,255,0.10) !important; margin: 1.35rem 0 !important; }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
            padding-top: 0.9rem !important;
        }
        h1 {
            font-size: 1.1rem !important;
            line-height: 1.25 !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto;
            flex-wrap: nowrap;
        }
        .stTabs [data-baseweb="tab"] {
            min-width: max-content;
            padding: 6px 12px;
            font-size: 0.76rem;
        }
        div[data-testid="metric-container"] {
            padding: 12px 13px;
        }
        div[data-testid="metric-container"] [data-testid="stMetricValue"] {
            font-size: 1.08rem !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label {
            flex: 1 1 calc(50% - 8px);
            justify-content: center;
        }
        .app-hero h1 {
            font-size: 1.68rem !important;
        }
        .hero-row {
            align-items: flex-start;
            flex-direction: column;
        }
        .viewer-pill {
            width: 100%;
            justify-content: center;
            font-size: 0.78rem;
        }
        .signal-grid {
            grid-template-columns: 1fr;
        }
        .risk-grid {
            grid-template-columns: 1fr;
        }
        .focus-title {
            min-height: auto;
            padding-top: 0.55rem;
        }
        .focus-title .name {
            font-size: 1.42rem;
        }
        .focus-title .ticker {
            font-size: 0.92rem;
        }
        .hero-title {
            gap: 9px;
        }
        div[data-testid="stPlotlyChart"] {
            min-height: 430px;
            margin-top: 0.2rem;
            margin-bottom: 1.15rem;
            overflow: visible !important;
        }
        div[data-testid="stPlotlyChart"] .modebar {
            display: none !important;
        }
        div[data-testid="stPlotlyChart"] .js-plotly-plot,
        div[data-testid="stPlotlyChart"] .plotly,
        div[data-testid="stPlotlyChart"] .main-svg {
            min-height: 430px !important;
            max-height: none !important;
            overflow: visible !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ── 상수 ───────────────────────────────────────────────────────────────────────
DELTA_OPTIONS  = {"90일": 90, "180일": 180, "1년": 365, "2년": 730, "4년": 9999}
DATA_PERIOD = "4y"
RECENT_TICKER_LIMIT = 12

MA_COLORS = {
    "MA20":  "#2196F3",
    "MA60":  "#FF9800",
    "MA120": "#F44336",
    "MA200": "#9C27B0",
}

# ── 숫자 포맷 헬퍼 ─────────────────────────────────────────────────────────────
def fmt_price(v):
    try: return f"${float(v):.2f}"
    except: return "N/A"

def fmt_pct(v, sign=False):
    try:
        f = float(v)
        return f"{f:+.2f}%" if sign else f"{f:.2f}%"
    except: return "N/A"

def fmt_1f(v):
    try: return f"{float(v):.1f}"
    except: return "N/A"

def fmt_int(v):
    try: return f"{int(float(v)):,}"
    except: return "N/A"

def safe_float(val):
    try: return float(val)
    except: return None

def normalize_ticker(value: str) -> str:
    ticker = value.strip().upper().replace(" ", "")
    if ticker.endswith((".KS", ".KQ")):
        return ""
    return ticker

def load_recent_tickers() -> list[str]:
    tickers = st.session_state.get("recent_tickers", [])
    return [
        normalize_ticker(ticker)
        for ticker in tickers
        if isinstance(ticker, str) and normalize_ticker(ticker)
    ][:RECENT_TICKER_LIMIT]

def save_recent_ticker(ticker: str):
    ticker = normalize_ticker(ticker)
    if not ticker:
        return
    recent = [item for item in load_recent_tickers() if item != ticker]
    recent.insert(0, ticker)
    st.session_state.recent_tickers = recent[:RECENT_TICKER_LIMIT]

def clear_recent_tickers():
    st.session_state.recent_tickers = []

def unique_tickers(tickers) -> list[str]:
    result = []
    for ticker in tickers:
        normalized = normalize_ticker(str(ticker))
        if normalized and normalized not in result:
            result.append(normalized)
    return result

def ticker_name(ticker: str) -> str:
    return TICKER_CONFIGS.get(ticker, ticker)

def has_rsi_puddle_signal(rsi, puddle) -> bool:
    try:
        rsi_val = float(rsi)
        puddle_text = str(puddle) if pd.notna(puddle) else ''
        return rsi_val <= 30 and any(ch.isalpha() for ch in puddle_text)
    except Exception:
        return False

@st.cache_resource
def get_visit_state():
    return {
        'total_views': 0,
        'sessions': {},
    }

def get_view_stats():
    state = get_visit_state()
    now = time.time()

    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        state['total_views'] += 1

    session_id = st.session_state.session_id
    state['sessions'][session_id] = now

    active_cutoff = now - 300
    state['sessions'] = {
        sid: ts for sid, ts in state['sessions'].items()
        if ts >= active_cutoff
    }
    return state['total_views'], len(state['sessions'])

def is_us_market_open(now: datetime | None = None) -> bool:
    eastern_now = now or datetime.now(ZoneInfo("America/New_York"))
    market_open = eastern_now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = eastern_now.replace(hour=16, minute=0, second=0, microsecond=0)
    return eastern_now.weekday() < 5 and market_open <= eastern_now <= market_close

# ── 캐싱 ───────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def load_common_data(period: str) -> dict:
    return fetch_common_market_data(period=period)

@st.cache_data(ttl=1800, show_spinner=False)
def load_ticker_data(ticker: str, name: str, period: str, delta: int, _cache_key: str) -> pd.DataFrame:
    common = load_common_data(period)
    return process_stock_data(ticker, name, common, period=period, delta=delta)

@st.cache_data(ttl=1800, show_spinner=False)
def load_market_summary_rows(period: str, delta: int, _cache_key: str, extra_tickers: tuple[str, ...] = ()) -> pd.DataFrame:
    common = load_common_data(period)
    summary_tickers = unique_tickers([*TICKER_CONFIGS.keys(), *extra_tickers])
    batch_data = fetch_batch_stock_data(summary_tickers, period)
    rows = []
    for ticker in summary_tickers:
        name = ticker_name(ticker)
        try:
            d = process_stock_frame(batch_data.get(ticker, pd.DataFrame()), ticker, name, common, delta=delta)
            if d.empty:
                continue
            lat = d.iloc[-1]
            rows.append({
                '종목':          name,
                '종가':          safe_float(lat.get('Close')),
                'Change(%)':     safe_float(lat.get('Change(%)')),
                '2sigma(%)':     safe_float(lat.get('2sigma(%)')),
                'RSI':           safe_float(lat.get('RSI')),
                'FG/RSI signal': lat.get('FG/RSI signal', ''),
                'Puddle':        lat.get('Puddle', ''),
            })
        except Exception:
            continue
    return pd.DataFrame(rows)

# ── 차트 공통 테마 ─────────────────────────────────────────────────────────────
CHART_THEME = dict(
    plot_bgcolor='#061323',
    paper_bgcolor='#061323',
    font=dict(family='DM Sans, sans-serif', color='#8e8e93', size=12),
    legend=dict(
        orientation='h', yanchor='bottom', y=1.025, xanchor='right', x=1,
        font=dict(size=11), bgcolor='rgba(0,0,0,0)', bordercolor='rgba(255,255,255,0.10)',
    ),
    xaxis_rangeslider_visible=False,
    margin=dict(l=50, r=16, t=54, b=64),
)
GRID = dict(showgrid=True, gridcolor='rgba(255,255,255,0.07)', zeroline=False)
MAIN_CHART_HEIGHT = 460
SIGNAL_CHART_HEIGHT = 500

def get_date_axis(df: pd.DataFrame) -> dict:
    dates = pd.to_datetime(df['Date']).dropna().drop_duplicates().sort_values()
    if dates.empty:
        return dict(automargin=True)

    span_days = (dates.iloc[-1] - dates.iloc[0]).days
    if span_days <= 120:
        freq, label_format = '2W-MON', '%m.%d'
    elif span_days <= 220:
        freq, label_format = 'MS', '%m.%d'
    elif span_days <= 420:
        freq, label_format = '2MS', '%y.%m'
    elif span_days <= 800:
        freq, label_format = 'QS', '%y.%m'
    else:
        freq, label_format = '2QS', '%y.%m'

    targets = pd.date_range(dates.iloc[0], dates.iloc[-1], freq=freq)
    target_dates = [dates.iloc[0], *targets, dates.iloc[-1]]
    tick_dates = []
    for target in target_dates:
        pos = dates.searchsorted(pd.Timestamp(target), side='left')
        if pos >= len(dates):
            pos = len(dates) - 1
        tick = dates.iloc[pos]
        if not tick_dates or tick != tick_dates[-1]:
            tick_dates.append(tick)

    return dict(
        tickmode='array',
        tickvals=tick_dates,
        ticktext=[d.strftime(label_format) for d in tick_dates],
        range=[dates.iloc[0], dates.iloc[-1]],
        automargin=True,
    )

# ── 캔들스틱 차트 ─────────────────────────────────────────────────────────────
def build_candlestick_chart(df: pd.DataFrame, name: str) -> go.Figure:
    date_axis = get_date_axis(df)
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.60, 0.20, 0.20],
        vertical_spacing=0.025,
    )

    fig.add_trace(go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name='Price',
        increasing_line_color='#64a8ff', increasing_fillcolor='#64a8ff',
        decreasing_line_color='#f85149', decreasing_fillcolor='#f85149',
        whiskerwidth=0.4,
    ), row=1, col=1)

    for ma, color in MA_COLORS.items():
        if ma in df.columns and df[ma].notna().any():
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df[ma], name=ma,
                line=dict(color=color, width=1.4), mode='lines',
            ), row=1, col=1)

    if 'Puddle' in df.columns:
        puddle_df = df[df['Puddle'].str.contains(r'[a-zA-Z]', na=False)]
        if not puddle_df.empty:
            fig.add_trace(go.Scatter(
                x=puddle_df['Date'], y=puddle_df['Low'] * 0.982,
                mode='markers', name='Puddle',
                marker=dict(symbol='triangle-up', size=10, color='#ffcc66',
                            line=dict(width=1, color='white')),
            ), row=1, col=1)

    if 'RSI' in df.columns and df['RSI'].notna().any():
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['RSI'], name='RSI',
            line=dict(color='#d2a679', width=1.5),
        ), row=2, col=1)
        fig.add_hline(y=70, line=dict(color='#f85149', width=1, dash='dot'), row=2, col=1)
        fig.add_hline(y=30, line=dict(color='#64a8ff', width=1, dash='dot'), row=2, col=1)
        fig.update_yaxes(
            title_text='RSI', range=[0, 100], row=2, col=1,
            tickfont=dict(color='#8e8e93', size=10),
            title=dict(font=dict(color='#8e8e93', size=11)),
        )

    if 'VIX' in df.columns and df['VIX'].notna().any():
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['VIX'], name='VIX',
            line=dict(color='#79c0ff', width=1.5),
            fill='tozeroy', fillcolor='rgba(121,192,255,0.07)',
        ), row=3, col=1)
        fig.add_hline(y=25, line=dict(color='#64a8ff', width=1, dash='dot'), row=3, col=1)
        fig.update_yaxes(
            title_text='VIX', row=3, col=1,
            tickfont=dict(color='#8e8e93', size=10),
            title=dict(font=dict(color='#8e8e93', size=11)),
        )

    fig.update_layout(
        **CHART_THEME,
        height=MAIN_CHART_HEIGHT,
    )
    for r in [1, 2, 3]:
        fig.update_xaxes(
            **GRID, **date_axis, row=r, col=1,
            showticklabels=(r == 3),
            tickfont=dict(color='#8e8e93', size=10),
        )
        fig.update_yaxes(**GRID, row=r, col=1)

    return fig

# ── 라인 차트 ─────────────────────────────────────────────────────────────────
def build_line_chart(df: pd.DataFrame, name: str) -> go.Figure:
    date_axis = get_date_axis(df)
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.68, 0.32], vertical_spacing=0.022,
    )

    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Close'], name=f'{name} Close',
        line=dict(color='#f5f5f7', width=2),
    ), row=1, col=1)

    for ma, color in MA_COLORS.items():
        if ma in df.columns and df[ma].notna().any():
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df[ma], name=ma,
                line=dict(color=color, width=1.2, dash='dot'),
            ), row=1, col=1)

    if 'VIX1D>VIX' in df.columns:
        vix_signal_dates = df[df['VIX1D>VIX'] == 'BUY']['Date']
        if not vix_signal_dates.empty:
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode='lines', name='VIX1D > VIX',
                line=dict(color='#5ee4ff', width=2.2, dash='dot'),
                hoverinfo='skip',
            ), row=1, col=1)
            for d in vix_signal_dates:
                fig.add_vline(
                    x=d,
                    line=dict(color='rgba(94,228,255,0.46)', width=1.8, dash='dot'),
                    layer='below',
                    row=1,
                    col=1,
                )

    if 'RSI' in df.columns and 'Puddle' in df.columns:
        oversold  = df[df['RSI'] <= 30]
        puddle_df = df[df['Puddle'].str.contains(r'[a-zA-Z]', na=False)]
        overlap   = pd.merge(oversold, puddle_df, on='Date', how='inner')
        if not overlap.empty:
            fig.add_trace(go.Scatter(
                x=overlap['Date'], y=overlap['Close_x'],
                mode='markers', name='RSI ∩ Puddle',
                marker=dict(symbol='circle', size=9, color='#ffcc66',
                            line=dict(width=1.5, color='white')),
            ), row=1, col=1)

    if 'FG index' in df.columns and df['FG index'].notna().any():
        fg_df = df[df['FG index'].notna()]
        fg_zones = [
            (0, 25,  '극도 공포', 'rgba(248,81,73,0.14)'),
            (25, 45, '공포',     'rgba(210,153,34,0.12)'),
            (45, 55, '중립',     'rgba(88,166,255,0.10)'),
            (55, 75, '탐욕',     'rgba(100,168,255,0.12)'),
            (75, 100, '극도 탐욕', 'rgba(10,132,255,0.18)'),
        ]
        for y0, y1, label, color in fg_zones:
            fig.add_hrect(
                y0=y0, y1=y1,
                fillcolor=color, line_width=0,
                annotation_text=label, annotation_position='left',
                annotation_font=dict(size=10, color='#8e8e93'),
                row=2, col=1,
            )
        fig.add_trace(go.Scatter(
            x=fg_df['Date'], y=fg_df['FG index'], name='Fear & Greed',
            mode='lines',
            line=dict(color='#bc8cff', width=2.4, shape='spline'),
            hovertemplate='%{x|%Y-%m-%d}<br>F&G %{y:.0f}<extra></extra>',
        ), row=2, col=1)
        latest_fg = fg_df.iloc[-1]
        fig.add_trace(go.Scatter(
            x=[latest_fg['Date']], y=[latest_fg['FG index']], name='현재 F&G',
            mode='markers+text',
            marker=dict(size=13, color='#bc8cff', line=dict(width=2, color='#f5f5f7')),
            text=[f"{latest_fg['FG index']:.0f}"],
            textposition='middle right',
            textfont=dict(size=12, color='#f5f5f7'),
            hovertemplate='%{x|%Y-%m-%d}<br>현재 F&G %{y:.0f}<extra></extra>',
        ), row=2, col=1)
        for level in [25, 45, 55, 75]:
            fig.add_hline(y=level, line=dict(color='rgba(138,168,192,0.24)', width=1, dash='dot'), row=2, col=1)
        fig.add_hline(y=50, line=dict(color='#0a84ff', width=1.4, dash='solid'), row=2, col=1)
        fig.update_yaxes(
            title_text='F&G', range=[0, 100], row=2, col=1,
            tickfont=dict(color='#8e8e93', size=10),
            title=dict(font=dict(color='#8e8e93', size=11)),
        )

    fig.update_layout(
        **CHART_THEME,
        height=SIGNAL_CHART_HEIGHT,
    )
    for r in [1, 2]:
        fig.update_xaxes(
            **GRID, **date_axis, row=r, col=1,
            showticklabels=(r == 2),
            tickfont=dict(color='#8e8e93', size=10),
        )
        fig.update_yaxes(**GRID, row=r, col=1)

    return fig

# ── 테이블 스타일 ───────────────────────────────────────────────────────────────
def style_table(df: pd.DataFrame):
    display_cols = [
        'Date', 'Close', 'Change(%)', '2sigma(%)',
        'RSI', 'FG index', 'FG/RSI signal', 'SS Signal',
        'Puddle', 'VIX', 'VIX1D', 'VIX1D>VIX', 'SKEW', '10Y Treasury',
    ]
    existing = [c for c in display_cols if c in df.columns]
    sub = df[existing].iloc[::-1].copy()

    # 화면 표시용 숫자 정리
    if 'Date' in sub.columns:
        sub['Date'] = pd.to_datetime(sub['Date']).dt.strftime('%Y-%m-%d')
    numeric_cols = [
        'Close', 'Change(%)', '2sigma(%)', 'RSI', 'FG index',
        'VIX', 'VIX1D', 'SKEW', '10Y Treasury',
    ]
    for col in numeric_cols:
        if col in sub.columns:
            sub[col] = pd.to_numeric(sub[col], errors='coerce')

    def color_row(row):
        styles = [''] * len(row)
        idx = list(row.index)
        def si(col): return idx.index(col) if col in idx else -1

        ci  = si('Change(%)')
        sci = si('2sigma(%)')
        ri  = si('RSI')
        pi  = si('Puddle')

        def bg_prefix(style):
            return f"{style}; " if style.startswith('background') else ''

        # 라인 차트의 RSI ∩ Puddle 동그라미와 같은 조건
        if ri >= 0 and pi >= 0:
            try:
                if has_rsi_puddle_signal(row.iloc[ri], row.iloc[pi]):
                    styles = ['background-color: rgba(188,140,255,0.20)'] * len(styles)
            except: pass

        # 2sigma 배경
        if ci >= 0 and sci >= 0:
            try:
                chg = float(row.iloc[ci]) if pd.notna(row.iloc[ci]) else 0
                sig = float(row.iloc[sci]) if pd.notna(row.iloc[sci]) else 0
                if chg < -sig and not styles[ci].startswith('background'):
                    styles = ['background-color: rgba(210,153,34,0.18)'] * len(styles)
            except: pass

        # Change(%) 글자색
        if ci >= 0 and pd.notna(row.iloc[ci]) and row.iloc[ci] != '':
            try:
                v = float(row.iloc[ci])
                bg = bg_prefix(styles[ci])
                styles[ci] = f'{bg}color: #f85149; font-weight:600' if v < 0 else \
                             f'{bg}color: #64a8ff; font-weight:600' if v > 0 else styles[ci]
            except: pass

        # RSI
        if ri >= 0 and pd.notna(row.iloc[ri]) and row.iloc[ri] != '':
            try:
                v = float(row.iloc[ri])
                bg = bg_prefix(styles[ri])
                styles[ri] = f'{bg}color: #64a8ff; font-weight:600' if v <= 30 else \
                             f'{bg}color: #f85149; font-weight:600' if v >= 70 else styles[ri]
            except: pass

        # VIX
        vi = si('VIX')
        if vi >= 0 and pd.notna(row.iloc[vi]) and row.iloc[vi] != '':
            try:
                if float(row.iloc[vi]) > 25:
                    styles[vi] = f'{bg_prefix(styles[vi])}color: #64a8ff; font-weight:600'
            except: pass

        # SKEW
        ski = si('SKEW')
        if ski >= 0 and pd.notna(row.iloc[ski]) and row.iloc[ski] != '':
            try:
                v = float(row.iloc[ski])
                bg = bg_prefix(styles[ski])
                styles[ski] = f'{bg}color: #f85149; font-weight:600' if v >= 155 else \
                              f'{bg}color: #64a8ff; font-weight:600' if v <= 127 else styles[ski]
            except: pass

        return styles

    formatters = {
        'Close':        lambda x: f"${x:,.2f}",
        'Change(%)':   lambda x: f"{x:+.2f}%",
        '2sigma(%)':   lambda x: f"{x:.1f}%",
        'RSI':         lambda x: f"{x:.1f}",
        'FG index':    lambda x: f"{int(round(x))}",
        'VIX':         lambda x: f"{x:.1f}",
        'VIX1D':       lambda x: f"{x:.1f}",
        'SKEW':        lambda x: f"{x:.1f}",
        '10Y Treasury': lambda x: f"{x:.2f}%",
    }
    existing_formatters = {
        col: formatter for col, formatter in formatters.items()
        if col in sub.columns
    }

    return (
        sub.style
        .apply(color_row, axis=1)
        .format(existing_formatters, na_rep='—')
    )

def format_table_value(col: str, value):
    if pd.isna(value) or value == '':
        return '—'
    try:
        if col in ['Close', '종가']:
            return f"${float(value):,.2f}"
        if col == 'Change(%)':
            return f"{float(value):+.2f}%"
        if col == '2sigma(%)':
            return f"{float(value):.1f}%"
        if col in ['RSI', 'VIX', 'VIX1D', 'SKEW']:
            return f"{float(value):.1f}"
        if col == 'FG index':
            return f"{int(round(float(value)))}"
        if col == '10Y Treasury':
            return f"{float(value):.2f}%"
    except Exception:
        pass
    return str(value)

def table_cell_class(col: str, value) -> str:
    classes = []
    if col in ['Close', '종가', 'Change(%)', '2sigma(%)', 'RSI', 'FG index', 'VIX', 'VIX1D', 'SKEW', '10Y Treasury']:
        classes.append('num')
    try:
        num = float(value)
        if col == 'Change(%)':
            classes.append('pos' if num > 0 else 'neg' if num < 0 else '')
        if col == 'RSI':
            classes.append('cool' if num <= 30 else 'hot' if num >= 70 else '')
    except Exception:
        pass
    return ' '.join(c for c in classes if c)

def render_glass_table(df: pd.DataFrame, columns: list[str], height_px: int = 520, newest_first: bool = False):
    existing = [col for col in columns if col in df.columns]
    if not existing:
        return
    view = df[existing].copy()
    if newest_first and 'Date' in view.columns:
        view['Date'] = pd.to_datetime(view['Date'])
        view = view.sort_values('Date', ascending=False)

    header = ''.join(f"<th>{escape(col)}</th>" for col in existing)
    body_rows = []
    for _, row in view.iterrows():
        row_classes = []
        if {'RSI', 'Puddle'}.issubset(view.columns) and has_rsi_puddle_signal(row.get('RSI'), row.get('Puddle')):
            row_classes.append('signal-row')
        try:
            if {'Change(%)', '2sigma(%)'}.issubset(view.columns):
                if float(row.get('Change(%)')) < -float(row.get('2sigma(%)')):
                    row_classes.append('sigma-row')
        except Exception:
            pass
        cells = []
        for col in existing:
            value = row.get(col)
            if col == 'Date' and pd.notna(value):
                value = pd.to_datetime(value).strftime('%Y-%m-%d')
            cls = table_cell_class(col, value)
            class_attr = f" class='{cls}'" if cls else ''
            cells.append(f"<td{class_attr}>{escape(format_table_value(col, value))}</td>")
        body_rows.append(f"<tr class='{' '.join(row_classes)}'>{''.join(cells)}</tr>")

    st.markdown(
        f"""
        <div class="glass-table-wrap" style="max-height:{height_px}px">
          <table class="glass-table">
            <thead><tr>{header}</tr></thead>
            <tbody>{''.join(body_rows)}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── 전체 종목 요약 ─────────────────────────────────────────────────────────────
def render_market_summary(period: str, delta: int, cache_key: str, extra_tickers: tuple[str, ...] = ()):
    with st.expander("Market Overview", expanded=False):
        with st.spinner("Market Overview를 불러오는 중..."):
            summary_df = load_market_summary_rows(period, delta, cache_key, extra_tickers)

        if not summary_df.empty:
            render_glass_table(
                summary_df,
                ['종목', '종가', 'Change(%)', '2sigma(%)', 'RSI', 'FG/RSI signal', 'Puddle'],
                height_px=420,
            )
        else:
            st.info("전체 종목 데이터를 아직 가져오지 못했습니다.")


def render_signal_cards(df: pd.DataFrame):
    def recent_rows(rows, limit=3):
        if rows.empty:
            return rows
        ordered = rows.copy()
        ordered['Date'] = pd.to_datetime(ordered['Date'])
        return ordered.sort_values('Date', ascending=False).head(limit)

    def make_items(rows, value_col=None, date_format='%y.%m.%d'):
        items = []
        for _, row in rows.iterrows():
            date = pd.to_datetime(row['Date']).strftime(date_format)
            value = row.get(value_col, '') if value_col else ''
            items.append((date, str(value) if pd.notna(value) and value else 'Signal'))
        return items

    puddle_items = make_items(
        recent_rows(df[df['Puddle'].str.contains(r'[a-zA-Z]', na=False)]),
        'Puddle',
    ) if 'Puddle' in df.columns else []

    vix_items = make_items(
        recent_rows(df[df['VIX1D>VIX'] == 'BUY']),
    ) if 'VIX1D>VIX' in df.columns else []

    stochastic_items = make_items(
        recent_rows(df[df['SS Signal'].isin(['Buy', 'Sell'])]),
        'SS Signal',
    ) if 'SS Signal' in df.columns else []

    if {'Date', 'RSI', 'Puddle'}.issubset(df.columns):
        rsi_puddle_rows = recent_rows(df[
            df.apply(lambda row: has_rsi_puddle_signal(row.get('RSI'), row.get('Puddle')), axis=1)
        ])
        rsi_puddle_items = []
        for _, row in rsi_puddle_rows.iterrows():
            date = pd.to_datetime(row['Date']).strftime('%y.%m.%d')
            rsi = safe_float(row.get('RSI'))
            rsi_text = f"RSI {rsi:.1f}" if rsi is not None else "RSI —"
            puddle = str(row.get('Puddle', '')) if pd.notna(row.get('Puddle')) else ''
            rsi_puddle_items.append((date, f"{rsi_text} · {puddle}"))
    else:
        rsi_puddle_items = []

    cards = [
        ('Puddle', puddle_items, '#bf5af2'),
        ('RSI & Puddle', rsi_puddle_items, '#ff9f0a'),
        ('VIX1D > VIX', vix_items, '#0a84ff'),
        ('Stochastic', stochastic_items, '#64a8ff'),
    ]
    html_cards = []
    for title, items, accent in cards:
        body = ''.join(
            f"<div class='signal-item'><span class='signal-date'>{escape(date)}</span>"
            f"<span>{escape(value)}</span></div>"
            for date, value in items
        )
        if not body:
            body = "<div class='signal-empty'>최근 신호 없음</div>"
        html_cards.append(
            f"<div class='signal-card' style='--accent:{accent}'>"
            f"<div class='signal-title'><span class='signal-dot'></span>{escape(title)}</div>"
            f"{body}</div>"
        )

    st.markdown(f"<div class='signal-grid'>{''.join(html_cards)}</div>", unsafe_allow_html=True)


def status_color(level: str) -> str:
    return {
        'opportunity': '#64a8ff',
        'safe': '#8ec5ff',
        'neutral': '#a1a1aa',
        'caution': '#ffcc00',
        'risk': '#ff453a',
    }.get(level, '#a1a1aa')


def render_risk_metrics(metrics):
    cards = []
    for metric in metrics:
        accent = status_color(metric['level'])
        cards.append(
            f"<div class='risk-card' style='--accent:{accent}'>"
            f"<div class='risk-top'><span>{escape(metric['label'])}</span>"
            f"<span class='risk-badge'>{escape(metric['status'])}</span></div>"
            f"<div class='risk-main'>{escape(metric['value'])}</div>"
            f"<div class='risk-caption'>{escape(metric['caption'])}</div>"
            f"</div>"
        )
    st.markdown(f"<div class='risk-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def rsi_status(value):
    if value is None:
        return ('neutral', 'N/A', '데이터 없음')
    if value <= 30:
        return ('opportunity', '과매도', '반등 후보 구간')
    if value >= 70:
        return ('risk', '과매수', '단기 과열 주의')
    return ('neutral', '중립', '추세 확인 구간')


def vix_status(value):
    if value is None:
        return ('neutral', 'N/A', '데이터 없음')
    if value > 25:
        return ('opportunity', '변동성 급등', '공포성 매수 기회')
    if value < 15:
        return ('safe', '안정', '낮은 변동성')
    return ('neutral', '보통', '평균 변동성')


def fg_status(value):
    if value is None:
        return ('neutral', 'N/A', '데이터 없음')
    if value >= 75:
        return ('risk', '극도 탐욕', '과열 리스크')
    if value >= 55:
        return ('caution', '탐욕', '추격 매수 주의')
    if value <= 25:
        return ('opportunity', '극도 공포', '역발상 관심')
    if value <= 45:
        return ('safe', '공포', '분할 접근 구간')
    return ('neutral', '중립', '방향성 대기')


def skew_status(value):
    if value is None:
        return ('neutral', 'N/A', '데이터 없음')
    if value >= 155:
        return ('risk', '고위험', '꼬리 리스크 확대')
    if value <= 127:
        return ('safe', '저위험', '왜도 부담 완화')
    return ('neutral', '보통', '평균 리스크')


def treasury_status(value):
    if value is None:
        return ('neutral', 'N/A', '데이터 없음')
    if value >= 5:
        return ('risk', '고금리', '밸류에이션 압박')
    if value >= 4.5:
        return ('caution', '금리 부담', '성장주 할인율 주의')
    if value <= 3.5:
        return ('safe', '완화', '금리 부담 낮음')
    return ('neutral', '보통', '중립 금리 구간')


# ── 상단 컨트롤 ────────────────────────────────────────────────────────────────
base_tickers = list(TICKER_CONFIGS.keys())
recent_tickers = load_recent_tickers()
ticker_options = base_tickers + [ticker for ticker in recent_tickers if ticker not in base_tickers]
total_views, active_viewers = get_view_stats()
market_open = is_us_market_open()
market_dot_class = "open" if market_open else "closed"

st.markdown(
    f"""
    <div class="app-hero">
      <div class="hero-row">
        <div>
          <div class="hero-title">
            <span class="market-status-dot {market_dot_class}"></span>
            <h1>US Market Signals</h1>
          </div>
          <a class="creator-mark" href="https://www.threads.com/@30s_tech_j" target="_blank" rel="noopener noreferrer">30s_tech_j</a>
        </div>
        <div class="viewer-pill">
          <span class="viewer-dot"></span>
          <span><strong>{active_viewers:,}</strong>명 보는 중</span>
          <span>·</span>
          <span>누적 <strong>{total_views:,}</strong>명</span>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
delta_label = st.radio(
    "표시 범위",
    options=list(DELTA_OPTIONS.keys()),
    index=list(DELTA_OPTIONS.keys()).index("180일"),
    horizontal=True,
)
delta = DELTA_OPTIONS[delta_label]


# ── 메인 영역 ──────────────────────────────────────────────────────────────────
period = DATA_PERIOD
cache_key = f"{period}_{delta}"

st.markdown("<div class='section-label'>Watchlist</div>", unsafe_allow_html=True)
focus_preset, focus_custom = st.columns([1, 1])
with focus_preset:
    preset_ticker = st.selectbox(
        "Saved Tickers",
        ticker_options,
        format_func=lambda ticker: f"{ticker_name(ticker)} · {ticker}",
    )
with focus_custom:
    raw_custom_ticker = st.text_input(
        "직접 조회",
        placeholder="미국 주식/ETF 티커 예: AAPL, NVDA, VOO",
    )
    if recent_tickers and st.button("최근 티커 비우기", use_container_width=True):
        clear_recent_tickers()
        st.rerun()

custom_ticker = normalize_ticker(raw_custom_ticker)
if raw_custom_ticker.strip() and not custom_ticker:
    st.caption("한국 상장 종목/ETF는 현재 조회 대상에서 제외했습니다.")

if custom_ticker:
    selected_ticker = custom_ticker
    selected_name = ticker_name(custom_ticker)
else:
    selected_ticker = preset_ticker
    selected_name = ticker_name(selected_ticker)

summary_extra_tickers = tuple(unique_tickers([*recent_tickers, selected_ticker]))
render_market_summary(period, delta, cache_key, summary_extra_tickers)
st.markdown("---")

st.markdown(
    f"""
    <div class="focus-title">
      <div class="eyebrow">Watchlist</div>
      <div class="name">{escape(selected_name)} <span class="ticker">{escape(selected_ticker)}</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.spinner(f"{selected_name} 데이터 불러오는 중..."):
    df = load_ticker_data(selected_ticker, selected_name, period, delta, cache_key)

if df.empty:
    st.error(f"{selected_ticker} 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

if selected_ticker not in TICKER_CONFIGS:
    save_recent_ticker(selected_ticker)

table_df = load_ticker_data(
    selected_ticker,
    selected_name,
    period,
    DELTA_OPTIONS["4년"],
    f"{period}_{DELTA_OPTIONS['4년']}",
)
if table_df.empty:
    table_df = df

latest = df.iloc[-1]

# ── 메트릭 카드 ────────────────────────────────────────────────────────────────
close_val    = safe_float(latest.get('Close'))
change_val   = safe_float(latest.get('Change(%)'))
rsi_val      = safe_float(latest.get('RSI'))
vix_val      = safe_float(latest.get('VIX'))
fg_val       = safe_float(latest.get('FG index'))
skew_val     = safe_float(latest.get('SKEW'))
treasury_val = safe_float(latest.get('10Y Treasury'))

change_level = 'safe' if change_val is not None and change_val > 0 else \
               'caution' if change_val is not None and change_val < 0 else 'neutral'
rsi_level, rsi_state, rsi_caption = rsi_status(rsi_val)
vix_level, vix_state, vix_caption = vix_status(vix_val)
fg_level, fg_state, fg_caption = fg_status(fg_val)
skew_level, skew_state, skew_caption = skew_status(skew_val)
treasury_level, treasury_state, treasury_caption = treasury_status(treasury_val)

render_risk_metrics([
    {
        'label': '종가',
        'value': fmt_price(close_val),
        'status': fmt_pct(change_val, sign=True) if change_val is not None else 'N/A',
        'caption': '전일 대비 변화',
        'level': change_level,
    },
    {
        'label': 'RSI',
        'value': fmt_1f(rsi_val) if rsi_val is not None else 'N/A',
        'status': rsi_state,
        'caption': rsi_caption,
        'level': rsi_level,
    },
    {
        'label': 'VIX',
        'value': fmt_1f(vix_val) if vix_val is not None else 'N/A',
        'status': vix_state,
        'caption': vix_caption,
        'level': vix_level,
    },
    {
        'label': 'F&G',
        'value': fmt_int(fg_val) if fg_val is not None else 'N/A',
        'status': fg_state,
        'caption': fg_caption,
        'level': fg_level,
    },
    {
        'label': 'SKEW',
        'value': fmt_1f(skew_val) if skew_val is not None else 'N/A',
        'status': skew_state,
        'caption': skew_caption,
        'level': skew_level,
    },
    {
        'label': '10Y Treasury',
        'value': f"{treasury_val:.2f}%" if treasury_val is not None else 'N/A',
        'status': treasury_state,
        'caption': treasury_caption,
        'level': treasury_level,
    },
])

# ── 최근 신호 ──────────────────────────────────────────────────────────────────
st.markdown("### Signal Feed")
render_signal_cards(df)

st.markdown("")

# ── 탭 ────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Chart", "Signals", "Metrics"])

with tab1:
    st.plotly_chart(
        build_candlestick_chart(df, selected_name),
        use_container_width=True,
        config={'displayModeBar': False, 'responsive': True},
    )

with tab2:
    st.plotly_chart(
        build_line_chart(df, selected_name),
        use_container_width=True,
        config={'displayModeBar': False, 'responsive': True},
    )

with tab3:
    render_glass_table(
        table_df,
        [
            'Date', 'Close', 'Change(%)', '2sigma(%)', 'RSI',
            'FG index', 'FG/RSI signal', 'SS Signal', 'Puddle',
            'VIX', 'VIX1D', 'VIX1D>VIX', 'SKEW', '10Y Treasury',
        ],
        height_px=500,
        newest_first=True,
    )

    csv = table_df.copy()
    if 'Date' in csv.columns:
        csv['Date'] = pd.to_datetime(csv['Date']).dt.strftime('%Y-%m-%d')
    st.download_button(
        label="CSV 다운로드",
        data=csv.to_csv(index=False, encoding='utf-8-sig'),
        file_name=f"{selected_name}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
