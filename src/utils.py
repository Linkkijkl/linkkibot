import datetime
import calendar

import logging

logger = logging.getLogger(__name__)

def end_of_month(dt: datetime.datetime) -> datetime.datetime:
    """
    Returns the datetime of the last datetime of the same month

    Example:
    >>> end_of_month(datetime.datetime(2026, 9, 29, 16, 0, 55, 880885))
    datetime.datetime(2026, 9, 30, 23, 59, 59, 999999)
    """
    (first_weekday, number_of_days) = calendar.monthrange(dt.year, dt.month)
    last_date = datetime.date(dt.year, dt.month, number_of_days)
    tz = dt.tzinfo
    result = datetime.datetime.combine(last_date, datetime.time.max).replace(tzinfo=tz)
    logger.debug(f"end_of_month({dt}) -> {result}")
    return result

def end_of_week(dt: datetime.datetime, week_start: int = 0) -> datetime.datetime:
    """
    Returns the datetime of the last datetime of the same week
    Args:
        dt (datetime.datetime): datetime to get the last day of week based on
        week_start (int): 0=Monday, 6=Sunday

    Example:
    >>> end_of_week(datetime.datetime(2026, 9, 29, 16, 0, 55, 880885))
    datetime.datetime(2026, 10, 4, 23, 59, 59, 999999)
    """
    current_weekday = dt.weekday()
    days_to_end = (week_start + 6 - current_weekday) % 7
    last_date = (dt + datetime.timedelta(days=days_to_end)).date()
    tz = dt.tzinfo
    result = datetime.datetime.combine(last_date, datetime.time.max).replace(tzinfo=tz)
    logger.debug(f"end_of_month({dt}, {week_start}) -> {result}")
    return result