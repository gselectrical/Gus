#!/usr/bin/env python3
"""Put something in Gus's diary.

    calendar_add.py "Smith rewire" --start "thursday 2pm" --duration 3h \
        --where "14 Mill Lane" --remind 60 --remind 1440

Prints one line confirming what went in, which is what the assistant repeats
back over WhatsApp.
"""

from __future__ import annotations

import argparse
import sys

import gs_google
import timeparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title", help="what the job or appointment is")
    parser.add_argument("--start", required=True, help='when, e.g. "thursday 2pm" or ISO')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--duration", default="1h", help='how long, e.g. "3h", "90m"')
    group.add_argument("--end", help="explicit end time instead of a duration")
    parser.add_argument("--where", default="", help="address or location")
    parser.add_argument("--notes", default="", help="anything else worth recording")
    parser.add_argument("--calendar", default="primary", help="calendar id (default: primary)")
    parser.add_argument(
        "--remind",
        type=int,
        action="append",
        default=None,
        metavar="MINUTES",
        help="alert this many minutes before; repeatable (default: 60)",
    )
    parser.add_argument("--all-day", action="store_true", help="book the whole day")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        start = timeparse.parse(args.start)
        if args.end:
            end = timeparse.parse(args.end)
        else:
            end = start + timeparse.parse_duration(args.duration)
    except timeparse.TimeParseError as exc:
        print("Could not work out the time: %s" % exc, file=sys.stderr)
        return 2

    if end <= start:
        print("End time is not after the start time.", file=sys.stderr)
        return 2

    reminders = args.remind if args.remind is not None else [60]

    event = {
        "summary": args.title,
        "location": args.where,
        "description": args.notes,
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": m} for m in sorted(set(reminders))],
        },
    }

    if args.all_day:
        event["start"] = {"date": start.date().isoformat()}
        event["end"] = {"date": end.date().isoformat()}
    else:
        event["start"] = {"dateTime": start.isoformat(), "timeZone": "Europe/London"}
        event["end"] = {"dateTime": end.isoformat(), "timeZone": "Europe/London"}

    try:
        service = gs_google.calendar_service()
        created = service.events().insert(calendarId=args.calendar, body=event).execute()
    except gs_google.CredentialError as exc:
        print("Calendar not set up: %s" % exc, file=sys.stderr)
        return 1

    span = "all day" if args.all_day else "%s-%s" % (
        start.strftime("%-I:%M%p").lower().replace(":00", ""),
        end.strftime("%-I:%M%p").lower().replace(":00", ""),
    )
    where = " at %s" % args.where if args.where else ""
    print("Added: %s -- %s, %s%s" % (args.title, timeparse.humanise(start), span, where))
    print(created.get("htmlLink", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
