"""Turn the way Gus actually talks about time into a datetime.

The assistant passes user phrasing straight through, so this needs to cope
with "tomorrow 2pm", "monday 8am", "in 40m" and UK-style "25/08 14:00" as
well as plain ISO. Everything is resolved in Europe/London.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/London")

WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

_REL = re.compile(r"^in\s+(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)$")
_CLOCK = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", re.I)
_UK_DATE = re.compile(r"^(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?$")


class TimeParseError(ValueError):
    """Raised when a phrase can't be resolved to a point in time."""


def now() -> datetime:
    return datetime.now(TZ)


def _parse_clock(text: str) -> tuple[int, int]:
    """'2pm' -> (14, 0);  '08:30' -> (8, 30);  '9' -> (9, 0)."""
    m = _CLOCK.match(text.strip())
    if not m:
        raise TimeParseError("could not read a time from %r" % text)
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    meridiem = (m.group(3) or "").lower()
    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise TimeParseError("%r is not a valid time of day" % text)
    return hour, minute


def _next_weekday(target: int, from_date: date, allow_today: bool) -> date:
    delta = (target - from_date.weekday()) % 7
    if delta == 0 and not allow_today:
        delta = 7
    return from_date + timedelta(days=delta)


def parse(text: str, *, default_hour: int = 9) -> datetime:
    """Resolve a phrase to an aware datetime in Europe/London.

    Anything already ISO-shaped is used verbatim. Otherwise the phrase is
    split into an optional day part and an optional clock part, and whatever
    is missing falls back to today / `default_hour`.
    """
    raw = " ".join(text.strip().lower().split())
    if not raw:
        raise TimeParseError("no time given")

    # ISO first -- the assistant should prefer this, and it is unambiguous.
    try:
        stamp = datetime.fromisoformat(raw.replace("z", "+00:00"))
        return stamp.astimezone(TZ) if stamp.tzinfo else stamp.replace(tzinfo=TZ)
    except ValueError:
        pass

    rel = _REL.match(raw)
    if rel:
        amount, unit = int(rel.group(1)), rel.group(2)
        if unit.startswith(("m", "min")):
            return now() + timedelta(minutes=amount)
        if unit.startswith(("h", "hr", "hour")):
            return now() + timedelta(hours=amount)
        return now() + timedelta(days=amount)

    words = raw.split()
    today = now().date()
    day: date | None = None
    consumed = 0

    if words[0] == "today":
        day, consumed = today, 1
    elif words[0] == "tomorrow":
        day, consumed = today + timedelta(days=1), 1
    elif words[0] == "tonight":
        day, consumed = today, 1
        if len(words) == 1:
            words.append("8pm")
    elif words[0] == "next" and len(words) > 1 and words[1] in WEEKDAYS:
        day, consumed = _next_weekday(WEEKDAYS[words[1]], today, allow_today=False), 2
    elif words[0] in WEEKDAYS:
        day, consumed = _next_weekday(WEEKDAYS[words[0]], today, allow_today=True), 1
    else:
        uk = _UK_DATE.match(words[0])
        if uk:
            d, mth = int(uk.group(1)), int(uk.group(2))
            year = int(uk.group(3) or today.year)
            if year < 100:
                year += 2000
            try:
                day = date(year, mth, d)
            except ValueError as exc:
                raise TimeParseError("%r is not a real date" % words[0]) from exc
            consumed = 1

    remainder = " ".join(words[consumed:]).replace("at", "").strip()

    if remainder:
        hour, minute = _parse_clock(remainder)
    elif day is not None:
        hour, minute = default_hour, 0
    else:
        raise TimeParseError("could not understand %r as a date or time" % text)

    if day is None:
        day = today

    stamp = datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ)

    # A bare clock time that has already passed today means tomorrow.
    if consumed == 0 and stamp <= now():
        stamp += timedelta(days=1)

    return stamp


def parse_duration(text: str) -> timedelta:
    """'90m', '2h', '1h30', '3 hours' -> timedelta."""
    raw = " ".join(text.strip().lower().split())
    combined = re.match(r"^(\d+)\s*h(?:ours?|rs?)?\s*(\d+)?\s*(?:m|mins?|minutes?)?$", raw)
    if combined:
        hours = int(combined.group(1))
        minutes = int(combined.group(2) or 0)
        return timedelta(hours=hours, minutes=minutes)
    simple = re.match(r"^(\d+)\s*(m|mins?|minutes?|h|hours?|hrs?|d|days?)$", raw)
    if not simple:
        raise TimeParseError("could not read a duration from %r" % text)
    amount, unit = int(simple.group(1)), simple.group(2)
    if unit.startswith("m"):
        return timedelta(minutes=amount)
    if unit.startswith(("h", "hr")):
        return timedelta(hours=amount)
    return timedelta(days=amount)


def humanise(stamp: datetime) -> str:
    """Render a datetime the way it would be said out loud."""
    local = stamp.astimezone(TZ)
    today = now().date()
    if local.date() == today:
        prefix = "today"
    elif local.date() == today + timedelta(days=1):
        prefix = "tomorrow"
    elif (local.date() - today).days < 7:
        prefix = local.strftime("%A")
    else:
        prefix = local.strftime("%a %-d %b")
    return "%s at %s" % (prefix, local.strftime("%-I:%M%p").lower())


if __name__ == "__main__":
    import sys

    for phrase in sys.argv[1:]:
        try:
            print("%-24s -> %s" % (phrase, humanise(parse(phrase))))
        except TimeParseError as exc:
            print("%-24s -> ERROR: %s" % (phrase, exc))
