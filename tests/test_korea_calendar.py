"""KRX month-end helpers. Run: python -m pytest tests/ (or python tests/test_korea_calendar.py)."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import korea_signal_engine as eng  # noqa: E402


def test_year_end_is_closed():
    assert not eng.is_krx_trading_day(date(2026, 12, 31))     # Thursday, KRX closed
    assert eng.is_last_trading_day_of_month(date(2026, 12, 30))
    assert not eng.is_last_trading_day_of_month(date(2026, 12, 31))
    assert eng.trading_days_left_in_month(date(2026, 12, 30)) == 1
    assert eng.trading_days_left_in_month(date(2026, 12, 29)) == 2


def test_month_end_on_a_weekend():
    # Oct 31 2026 is a Saturday: Friday Oct 30 is the last trading day.
    assert eng.is_last_trading_day_of_month(date(2026, 10, 30))
    assert not eng.is_last_trading_day_of_month(date(2026, 10, 29))
    assert eng.trading_days_left_in_month(date(2026, 10, 30)) == 1


def test_calendar_month_end_that_trades():
    # Mar 31 2026 is a Tuesday and trades: the day after is in the next month.
    assert eng.is_last_trading_day_of_month(date(2026, 3, 31))
    assert eng.trading_days_left_in_month(date(2026, 3, 31)) == 1


def test_weekend_and_fixed_holiday_are_not_last_days():
    assert not eng.is_last_trading_day_of_month(date(2026, 10, 31))   # Saturday
    assert date(2026, 10, 9).weekday() == 4 and not eng.is_krx_trading_day(date(2026, 10, 9))   # 한글날, a Friday
    assert date(2026, 5, 5).weekday() == 1 and not eng.is_krx_trading_day(date(2026, 5, 5))     # 어린이날, a Tuesday
    assert eng.trading_days_left_in_month(date(2026, 10, 31)) == 0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
