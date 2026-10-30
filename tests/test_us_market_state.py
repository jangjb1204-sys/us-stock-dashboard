"""US session state + NYSE calendar. Run: python -m pytest tests/ (or python tests/test_us_market_state.py)."""
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import stock_analyzer as sa  # noqa: E402

ET = ZoneInfo('America/New_York')
KST = ZoneInfo('Asia/Seoul')

# Published NYSE full-day closures.
HOLIDAYS = {
    2026: {date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16), date(2026, 4, 3), date(2026, 5, 25),
           date(2026, 6, 19), date(2026, 7, 3), date(2026, 9, 7), date(2026, 11, 26), date(2026, 12, 25)},
    2027: {date(2027, 1, 1), date(2027, 1, 18), date(2027, 2, 15), date(2027, 3, 26), date(2027, 5, 31),
           date(2027, 6, 18), date(2027, 7, 5), date(2027, 9, 6), date(2027, 11, 25), date(2027, 12, 24)},
}


def test_holidays_match_published_calendar():
    for year, expected in HOLIDAYS.items():
        assert sa.nyse_holidays(year) == expected


def test_early_closes():
    assert sa.nyse_early_closes(2026) == {date(2026, 11, 27), date(2026, 12, 24)}
    assert sa.nyse_early_closes(2025) == {date(2025, 7, 3), date(2025, 11, 28), date(2025, 12, 24)}


def test_session_boundaries():
    cases = [
        ((2026, 10, 30, 3, 59), 'closed'), ((2026, 10, 30, 4, 0), 'pre'), ((2026, 10, 30, 9, 29), 'pre'),
        ((2026, 10, 30, 9, 30), 'open'), ((2026, 10, 30, 15, 59), 'open'), ((2026, 10, 30, 16, 0), 'after'),
        ((2026, 10, 30, 19, 59), 'after'), ((2026, 10, 30, 20, 0), 'closed'),
        ((2026, 10, 31, 11, 0), 'closed'),     # Saturday
        ((2026, 11, 26, 11, 0), 'holiday'),    # Thanksgiving
        ((2026, 11, 27, 12, 59), 'open'), ((2026, 11, 27, 13, 0), 'after'), ((2026, 11, 27, 17, 0), 'closed'),
    ]
    for (y, mo, d, h, mi), expected in cases:
        assert sa.us_market_state(datetime(y, mo, d, h, mi, tzinfo=ET))[0] == expected, (y, mo, d, h, mi)


def test_timezone_inputs():
    assert sa.us_market_state(datetime(2026, 10, 30, 23, 30, tzinfo=KST))[0] == 'open'   # 10:30 ET
    assert sa.us_market_state(datetime(2026, 10, 30, 9, 0))[0] == 'open'                 # naive = Chicago, 10:00 ET


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('PASS', name)
