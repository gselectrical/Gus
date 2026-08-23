#!/usr/bin/env python3
"""What's coming up.

    agenda.py            # today
    agenda.py --days 7   # the week
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta

import gs_google
import timeparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=1, help="how many days ahead (default: 1)")
    parser.add_argument("--calendar", default="primary", help="calendar id")
    args = parser.parse_args(argv)

    start = timeparse.now()
    window_end = (start + timedelta(days=args.days)).replace(hour=23, minute=59)

    try:
        service = gs_google.calendar_service()
        events = service.events().list(
            calendarId=args.calendar,
            timeMin=start.isoformat(),
            timeMax=window_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=50,
        ).execute().get("items", [])
    except gs_google.CredentialError as exc:
        print("Calendar not set up: %s" % exc, file=sys.stderr)
        return 1

    if not events:
        print("Nothing in the diary for the next %d day%s."
              % (args.days, "" if args.days == 1 else "s"))
        return 0

    for event in events:
        start_field = event["start"]
        if "date" in start_field:
            when = "%s (all day)" % start_field["date"]
        else:
            when = timeparse.humanise(timeparse.parse(start_field["dateTime"]))
        location = event.get("location")
        print("- %s: %s%s" % (when, event.get("summary", "(no title)"),
                              " [%s]" % location if location else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
