"""Shared helpers for menu notifications."""

from __future__ import annotations

import datetime as dt
import os
from zoneinfo import ZoneInfo

import requests


EASTERN_TIME = ZoneInfo("America/New_York")
HTTP_TIMEOUT_SECONDS = 15


def next_weekday(today: dt.date | None = None) -> dt.date:
    """Return the next Monday-Friday date in the school's local timezone."""
    if today is None:
        today = dt.datetime.now(EASTERN_TIME).date()

    menu_date = today + dt.timedelta(days=1)
    while menu_date.weekday() >= 5:
        menu_date += dt.timedelta(days=1)
    return menu_date


def required_environment_variable(name: str) -> str:
    """Return a required non-empty environment variable."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def send_notification(
    *, topic_stub: str, school_slug: str, message: str, title: str, menu_url: str
) -> None:
    """Send a menu notification and fail if ntfy does not accept it."""
    response = requests.post(
        f"https://ntfy.sh/{topic_stub}-{school_slug}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Tags": "plate_with_cutlery",
            "Markdown": "yes",
            "Actions": f"view, Website, {menu_url}",
        },
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
