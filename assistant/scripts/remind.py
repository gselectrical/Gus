#!/usr/bin/env python3
"""Set a reminder that actually makes the phone go off.

    remind.py "chase Batcheller Monkhouse" --at "monday 8am"

A server cannot touch the iPhone Clock app, so a reminder is a short calendar
entry with a popup alert on it -- the phone is already synced to that
calendar, so the alert lands the same way an alarm would.
"""

from __future__ import annotations

import argparse
import sys

import gs_google
import timeparse

PREFIX = "\N{BELL} "


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", help="what to be reminded about")
    parser.add_argument("--at", required=True, help='when, e.g. "monday 8am", "in 40m"')
    parser.add_argument("--notes", default="", help="extra detail for the reminder")
    parser.add_argument("--calendar", default="primary", help="calendar id")
    parser.add_argument(
        "--lead",
        type=int,
        default=0,
        help="alert this many minutes early (default: 0, i.e. on the dot)",
    )
    args = parser.parse_args(argv)

    try:
        when = timeparse.parse(args.at)
    except timeparse.TimeParseError as exc:
        print("Could not work out when: %s" % exc, file=sys.stderr)
        return 2

    if when <= timeparse.now():
        print("That time has already passed.", file=sys.stderr)
        return 2

    event = {
        "summary": PREFIX + args.text,
        "description": args.notes,
        "start": {"dateTime": when.isoformat(), "timeZone": "Europe/London"},
        "end": {"dateTime": (when + timeparse.parse_duration("15m")).isoformat(),
                "timeZone": "Europe/London"},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": max(0, args.lead)}],
        },
        "transparency": "transparent",  # keeps the day looking free
    }

    try:
        service = gs_google.calendar_service()
        service.events().insert(calendarId=args.calendar, body=event).execute()
    except gs_google.CredentialError as exc:
        print("Calendar not set up: %s" % exc, file=sys.stderr)
        return 1

    print("Reminder set: %s -- %s" % (args.text, timeparse.humanise(when)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
