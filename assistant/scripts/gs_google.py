"""Find whatever Google credentials this machine already has, and build a
Calendar service from them.

The assistant already reads the diary, so credentials exist somewhere on the
VM -- this looks in the usual places rather than making you set them up
again. Run it directly to see what it found:

    python3 gs_google.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/calendar"]

HOME = Path.home()
APP_DIR = Path(os.environ.get("GS_APP_DIR", HOME / "gs-app"))

# Checked in order; first hit wins.
TOKEN_CANDIDATES = [
    os.environ.get("GS_GOOGLE_TOKEN"),
    APP_DIR / "token.json",
    APP_DIR / "config" / "token.json",
    APP_DIR / ".credentials" / "token.json",
    HOME / ".config" / "gs-app" / "token.json",
    HOME / ".credentials" / "calendar.json",
    HOME / ".config" / "gcalcli" / "oauth",
]

CLIENT_SECRET_CANDIDATES = [
    os.environ.get("GS_GOOGLE_CLIENT_SECRET"),
    APP_DIR / "credentials.json",
    APP_DIR / "client_secret.json",
    APP_DIR / "config" / "credentials.json",
    HOME / ".config" / "gs-app" / "credentials.json",
]

SERVICE_ACCOUNT_CANDIDATES = [
    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
    APP_DIR / "service-account.json",
    APP_DIR / "config" / "service-account.json",
]


class CredentialError(RuntimeError):
    """No usable Google credentials were found."""


def _existing(candidates) -> list[Path]:
    found = []
    for entry in candidates:
        if not entry:
            continue
        path = Path(entry).expanduser()
        if path.is_file():
            found.append(path)
    return found


def _looks_like_service_account(path: Path) -> bool:
    try:
        with path.open() as handle:
            return json.load(handle).get("type") == "service_account"
    except (OSError, ValueError):
        return False


def load_credentials():
    """Return google credentials, or raise CredentialError explaining why not."""
    try:
        from google.oauth2.credentials import Credentials
        from google.oauth2.service_account import Credentials as ServiceCredentials
        from google.auth.transport.requests import Request
    except ImportError as exc:  # pragma: no cover - environment problem
        raise CredentialError(
            "google auth libraries are missing -- run assistant/install.sh"
        ) from exc

    for path in _existing(TOKEN_CANDIDATES):
        if _looks_like_service_account(path):
            continue
        try:
            creds = Credentials.from_authorized_user_file(str(path), SCOPES)
        except (ValueError, KeyError):
            continue
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            path.write_text(creds.to_json())
        if creds.valid:
            return creds

    for path in _existing(SERVICE_ACCOUNT_CANDIDATES) + _existing(TOKEN_CANDIDATES):
        if not _looks_like_service_account(path):
            continue
        subject = os.environ.get("GS_GOOGLE_IMPERSONATE")
        creds = ServiceCredentials.from_service_account_file(str(path), scopes=SCOPES)
        return creds.with_subject(subject) if subject else creds

    try:
        import google.auth

        creds, _ = google.auth.default(scopes=SCOPES)
        return creds
    except Exception:  # noqa: BLE001 - any failure here means "no ADC"
        pass

    raise CredentialError(
        "no Google credentials found.\n"
        "Looked in:\n  "
        + "\n  ".join(str(p) for p in TOKEN_CANDIDATES if p)
        + "\nSet GS_GOOGLE_TOKEN to the token file the assistant already uses, "
        "or run: python3 gs_google.py --authorise"
    )


def calendar_service():
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise CredentialError(
            "the Google API client is missing -- run assistant/install.sh"
        ) from exc

    return build("calendar", "v3", credentials=load_credentials(), cache_discovery=False)


def authorise() -> Path:
    """Run the OAuth flow and save a token for future runs."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    secrets = _existing(CLIENT_SECRET_CANDIDATES)
    if not secrets:
        raise CredentialError(
            "need an OAuth client file (credentials.json) to authorise.\n"
            "Create one at console.cloud.google.com -> APIs & Services -> "
            "Credentials -> OAuth client ID (Desktop app), download it to "
            f"{APP_DIR / 'credentials.json'}, then run this again."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets[0]), SCOPES)
    creds = flow.run_console() if hasattr(flow, "run_console") else flow.run_local_server(port=0)

    target = APP_DIR / "token.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(creds.to_json())
    target.chmod(0o600)
    return target


def _report() -> int:
    print("app dir:", APP_DIR)
    for label, candidates in (
        ("token", TOKEN_CANDIDATES),
        ("oauth client", CLIENT_SECRET_CANDIDATES),
        ("service account", SERVICE_ACCOUNT_CANDIDATES),
    ):
        found = _existing(candidates)
        print("%-16s %s" % (label + ":", found[0] if found else "-- none found --"))

    try:
        service = calendar_service()
    except CredentialError as exc:
        print("\nNOT WORKING:", exc)
        return 1

    calendars = service.calendarList().list(maxResults=20).execute().get("items", [])
    print("\nWorking. Calendars this account can see:")
    for entry in calendars:
        mark = "*" if entry.get("primary") else " "
        print("  %s %-40s %s" % (mark, entry.get("summary", "?"), entry.get("accessRole")))
    return 0


if __name__ == "__main__":
    if "--authorise" in sys.argv or "--authorize" in sys.argv:
        print("saved:", authorise())
    else:
        sys.exit(_report())
