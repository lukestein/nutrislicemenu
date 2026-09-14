"""Generate public iCalendar feeds from Newton's Nutrislice menus."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
from pathlib import Path

from calendar_config import (
    COMMON_SUMMARY_EXCLUSION_PATTERNS,
    SUMMARY_ALIASES,
    SUMMARY_CAPITALIZATIONS,
    SUMMARY_EMOJI_REPLACEMENTS,
    SUMMARY_RULES,
)
from menu_common import EASTERN_TIME
from menu_page import render_menu_page
from nutrislicemenu import (
    HIDE_SECTION_HEADERS,
    IGNORED_SECTIONS,
    SCHOOLS,
    get_menu_week,
)


CALENDAR_DOMAIN = "nutrislicemenu.lukestein"
DEFAULT_WEEKS = 4
MAX_SUMMARY_LENGTH = 140


def menu_url(school: dict[str, str], menu_date: dt.date) -> str:
    return (
        f"https://{school['district']}.nutrislice.com/menu/"
        f"{school['slug']}/lunch/{menu_date.isoformat()}"
    )


def week_starts(today: dt.date, number_of_weeks: int) -> list[dt.date]:
    """Return Sundays for the current week and following weeks."""
    current_sunday = today - dt.timedelta(days=(today.weekday() + 1) % 7)
    return [
        current_sunday + dt.timedelta(weeks=offset)
        for offset in range(number_of_weeks)
    ]


def _normal(value: str) -> str:
    return " ".join(value.split()).casefold()


def is_summary_item(school_slug: str, food_name: str) -> bool:
    """Return whether a food should appear in a compact event summary."""
    rules = SUMMARY_RULES.get(school_slug, {})
    excluded_names = {_normal(name) for name in rules.get("exact", set())}
    if _normal(food_name) in excluded_names:
        return False

    patterns = COMMON_SUMMARY_EXCLUSION_PATTERNS + rules.get("patterns", [])
    return not any(re.search(pattern, food_name, re.IGNORECASE) for pattern in patterns)


def compact_food_name(food_name: str) -> str:
    """Shorten a Nutrislice item and change Title Case to sentence style."""
    compact = SUMMARY_ALIASES.get(food_name, " ".join(food_name.split()).lower())
    for lowercase, preferred in SUMMARY_CAPITALIZATIONS.items():
        compact = re.sub(
            rf"(?<!\w){re.escape(lowercase)}(?!\w)",
            preferred,
            compact,
            flags=re.IGNORECASE,
        )
    for pattern, replacement in SUMMARY_EMOJI_REPLACEMENTS:
        compact = re.sub(pattern, replacement, compact, flags=re.IGNORECASE)
    return compact


def _capitalize_first_letter(value: str) -> str:
    """Capitalize the first alphabetic character without changing later words."""
    match = re.search(r"[A-Za-z]", value)
    if not match:
        return value
    index = match.start()
    return value[:index] + value[index].upper() + value[index + 1 :]


def event_summary(
    school: dict[str, str], menu_sections: dict[str, list[str]]
) -> str:
    """Build a compact, comma-separated calendar event title."""
    foods = []
    seen = set()
    for section_foods in menu_sections.values():
        for food_name in section_foods:
            if not is_summary_item(school["slug"], food_name):
                continue
            compact = _capitalize_first_letter(compact_food_name(food_name))
            key = compact.casefold()
            if key not in seen:
                foods.append(compact)
                seen.add(key)

    prefix = school["name"]
    if not foods:
        return prefix

    included = []
    for food in foods:
        candidate = f"{prefix}: {', '.join(included + [food])}"
        if included and len(candidate) > MAX_SUMMARY_LENGTH:
            break
        included.append(food)

    summary = f"{prefix}: {', '.join(included)}"
    if len(included) < len(foods):
        summary += ", …"
    return summary


def event_description(
    menu_sections: dict[str, list[str]], source_url: str
) -> str:
    """Render the full useful menu as plain text for a calendar body."""
    blocks = []
    for section, foods in menu_sections.items():
        if section in IGNORED_SECTIONS:
            continue
        lines = []
        if section not in HIDE_SECTION_HEADERS:
            lines.append(section)
        lines.extend(f"• {food}" for food in foods)
        blocks.append("\n".join(lines))
    blocks.append(f"Nutrislice menu: {source_url}")
    return "\n\n".join(blocks)


def escape_ical_text(value: str) -> str:
    """Escape an iCalendar TEXT value."""
    return (
        value.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def fold_ical_line(line: str, limit: int = 75) -> str:
    """Fold a content line without splitting a UTF-8 character."""
    physical_lines = []
    remaining = line
    first = True
    while remaining:
        available = limit if first else limit - 1
        byte_count = 0
        split_at = 0
        for index, character in enumerate(remaining):
            character_bytes = len(character.encode("utf-8"))
            if byte_count + character_bytes > available:
                break
            byte_count += character_bytes
            split_at = index + 1
        if split_at == 0:
            split_at = 1
        prefix = "" if first else " "
        physical_lines.append(prefix + remaining[:split_at])
        remaining = remaining[split_at:]
        first = False
    return "\r\n".join(physical_lines)


def serialize_calendar(
    school: dict[str, str],
    menus: dict[dt.date, dict[str, list[str]]],
    generated_at: dt.datetime,
) -> str:
    """Serialize one school's menus as an RFC 5545 calendar."""
    generated_utc = generated_at.astimezone(dt.timezone.utc)
    timestamp = generated_utc.strftime("%Y%m%dT%H%M%SZ")
    sequence = int(generated_utc.timestamp())
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//nutrislicemenu//School Lunch Calendars//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ical_text(school['name'] + ' lunch menu')}",
        f"X-WR-TIMEZONE:{EASTERN_TIME.key}",
        "X-PUBLISHED-TTL:PT6H",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
    ]

    for menu_date in sorted(menus):
        sections = menus[menu_date]
        if menu_date.weekday() >= 5 or not any(sections.values()):
            continue
        source_url = menu_url(school, menu_date)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{school['slug']}-{menu_date:%Y%m%d}@{CALENDAR_DOMAIN}",
                f"DTSTAMP:{timestamp}",
                f"LAST-MODIFIED:{timestamp}",
                f"SEQUENCE:{sequence}",
                f"DTSTART;VALUE=DATE:{menu_date:%Y%m%d}",
                f"DTEND;VALUE=DATE:{menu_date + dt.timedelta(days=1):%Y%m%d}",
                f"SUMMARY:{escape_ical_text(event_summary(school, sections))}",
                f"DESCRIPTION:{escape_ical_text(event_description(sections, source_url))}",
                f"URL:{source_url}",
                "TRANSP:TRANSPARENT",
                "STATUS:CONFIRMED",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_ical_line(line) for line in lines) + "\r\n"


def generate_calendars(
    output_dir: Path,
    today: dt.date | None = None,
    number_of_weeks: int = DEFAULT_WEEKS,
) -> list[Path]:
    """Fetch menus and write one calendar feed per configured school."""
    if today is None:
        today = dt.datetime.now(EASTERN_TIME).date()
    generated_at = dt.datetime.now(dt.timezone.utc)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = []
    menus_by_school = {}

    for school in SCHOOLS:
        menus = {}
        for week_start in week_starts(today, number_of_weeks):
            menus.update(get_menu_week(school["district"], school["slug"], week_start))
        menus_by_school[school["slug"]] = menus

        output_path = output_dir / f"{school['name'].lower()}.ics"
        output_path.write_text(
            serialize_calendar(school, menus, generated_at), encoding="utf-8", newline=""
        )
        output_paths.append(output_path)
        print(f"Wrote {output_path} with {sum(bool(v) for v in menus.values())} menus")

    page_path = output_dir / "index.html"
    page_path.write_text(
        render_menu_page(SCHOOLS, menus_by_school, today, generated_at, event_summary),
        encoding="utf-8",
    )
    output_paths.append(page_path)
    print(f"Wrote {page_path}")

    for asset_name in ("favicon.svg", "apple-touch-icon.png"):
        asset_path = output_dir / asset_name
        shutil.copyfile(Path(__file__).with_name(asset_name), asset_path)
        output_paths.append(asset_path)
        print(f"Wrote {asset_path}")

    for school in SCHOOLS:
        school_page_path = output_dir / school["name"].lower() / "index.html"
        school_page_path.parent.mkdir(parents=True, exist_ok=True)
        school_page_path.write_text(
            render_menu_page(
                [school], menus_by_school, today, generated_at, event_summary
            ),
            encoding="utf-8",
        )
        output_paths.append(school_page_path)
        print(f"Wrote {school_page_path}")

    return output_paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("_site"))
    parser.add_argument("--weeks", type=int, default=DEFAULT_WEEKS)
    args = parser.parse_args()
    generate_calendars(args.output_dir, number_of_weeks=args.weeks)


if __name__ == "__main__":
    main()
