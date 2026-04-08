"""
Utility to parse human-readable duration strings like '10 minutes', '2 hours', '1 day'
into timedelta objects.
"""

import re
from datetime import timedelta

# Pattern: optional number (int or float) followed by a time unit
_DURATION_PATTERN = re.compile(
    r'^\s*(\d+(?:\.\d+)?)\s*'
    r'(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|w)\s*$',
    re.IGNORECASE,
)

_UNIT_MAP = {
    's': 'seconds', 'sec': 'seconds', 'secs': 'seconds', 'second': 'seconds', 'seconds': 'seconds',
    'm': 'minutes', 'min': 'minutes', 'mins': 'minutes', 'minute': 'minutes', 'minutes': 'minutes',
    'h': 'hours', 'hr': 'hours', 'hrs': 'hours', 'hour': 'hours', 'hours': 'hours',
    'd': 'days', 'day': 'days', 'days': 'days',
    'w': 'weeks', 'week': 'weeks', 'weeks': 'weeks',
}

DEFAULT_DURATION = timedelta(minutes=10)


def parse_tracking_duration(value: str) -> timedelta:
    """Parse a tracking_duration string into a timedelta.

    Supports formats like:
        '10 minutes', '5 seconds', '2 hours', '1 day', '30m', '2h', '1w'

    Returns DEFAULT_DURATION (10 minutes) if the string cannot be parsed.
    """
    if not value or not isinstance(value, str):
        return DEFAULT_DURATION

    match = _DURATION_PATTERN.match(value.strip())
    if not match:
        return DEFAULT_DURATION

    amount = float(match.group(1))
    unit_raw = match.group(2).lower()
    unit = _UNIT_MAP.get(unit_raw)
    if not unit:
        return DEFAULT_DURATION

    return timedelta(**{unit: amount})
