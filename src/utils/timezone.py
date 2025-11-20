"""
Timezone utilities for UTC+4 timezone handling.
"""

from datetime import datetime, timezone, timedelta

# UTC+4 timezone
UTC_PLUS_4 = timezone(timedelta(hours=4))


def now_utc4() -> datetime:
    """
    Get current time in UTC+4 timezone.
    
    Returns:
        Current datetime in UTC+4
    """
    return datetime.now(UTC_PLUS_4)


def utcnow_utc4() -> datetime:
    """
    Get current time in UTC+4 timezone.
    Alias for now_utc4() for compatibility with existing code.
    
    Returns:
        Current datetime in UTC+4
    """
    return now_utc4()

