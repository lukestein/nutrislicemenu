"""Render the fast, static web page published with the calendar feeds."""

from __future__ import annotations

import datetime as dt
import html
from collections.abc import Callable

from menu_common import EASTERN_TIME
from nutrislicemenu import HIDE_SECTION_HEADERS, IGNORED_SECTIONS


PUBLIC_BASE_URL = "https://lukestein.com/nutrislicemenu"
GOOGLE_ADD_URL = "https://calendar.google.com/calendar/u/0/r/settings/addbyurl"
WEB_SUMMARY_REPLACEMENTS = {
    "🌭": "hot dog",
    "🍕": "pizza",
    "🥗": "salad",
}
MENU_DAY_ROLLOVER_HOUR = 13


def displayed_menu_dates(
    today: dt.date, generated_at: dt.datetime
) -> list[dt.date]:
    """Return eligible school days in the rolling menu window."""
    local_time = generated_at.astimezone(EASTERN_TIME)
    first_date = today
    if local_time.hour >= MENU_DAY_ROLLOVER_HOUR:
        first_date += dt.timedelta(days=1)
    return [
        first_date + dt.timedelta(days=offset)
        for offset in range(8)
        if (first_date + dt.timedelta(days=offset)).weekday() < 5
    ]


def format_date_range(first_date: dt.date, last_date: dt.date) -> str:
    if first_date == last_date:
        return f"{first_date:%B} {first_date.day}, {first_date.year}"
    if first_date.year == last_date.year and first_date.month == last_date.month:
        return f"{first_date:%B} {first_date.day}–{last_date.day}, {last_date.year}"
    if first_date.year == last_date.year:
        return (
            f"{first_date:%B} {first_date.day}–"
            f"{last_date:%B} {last_date.day}, {last_date.year}"
        )
    return (
        f"{first_date:%B} {first_date.day}, {first_date.year}–"
        f"{last_date:%B} {last_date.day}, {last_date.year}"
    )


def has_menu(menu_sections: dict[str, list[str]]) -> bool:
    """Return whether a day contains at least one posted food item."""
    return any(menu_sections.values())


def format_web_summary(compact_summary: str, school_name: str) -> str:
    """Convert a compact calendar title into a sentence-style web summary."""
    prefix = f"{school_name}: "
    if compact_summary.startswith(prefix):
        compact_summary = compact_summary[len(prefix) :]
    for emoji, food_name in WEB_SUMMARY_REPLACEMENTS.items():
        compact_summary = compact_summary.replace(emoji, food_name)
    return compact_summary[:1].upper() + compact_summary[1:]


def _menu_sections(menu_sections: dict[str, list[str]]) -> str:
    blocks = []
    for section, foods in menu_sections.items():
        if section in IGNORED_SECTIONS:
            continue
        heading = ""
        if section not in HIDE_SECTION_HEADERS:
            heading = f'<h4>{html.escape(section)}</h4>'
        items = "".join(f"<li>{html.escape(food)}</li>" for food in foods)
        blocks.append(f'<div class="menu-section">{heading}<ul>{items}</ul></div>')
    return "".join(blocks)


def _day_card(
    school: dict[str, str],
    menu_date: dt.date,
    menu_sections: dict[str, list[str]],
    compact_summary: str,
    open_by_default: bool,
) -> str:
    day_label = menu_date.strftime("%A")
    date_label = f"{menu_date:%b} {menu_date.day}"
    source_url = (
        f"https://{school['district']}.nutrislice.com/menu/"
        f"{school['slug']}/lunch/{menu_date.isoformat()}"
    )
    if not has_menu(menu_sections):
        return f"""
        <div class="day empty">
          <div class="day-name"><strong>{day_label}</strong><span>{date_label}</span></div>
          <span class="empty-label">No menu posted</span>
        </div>"""

    compact_summary = format_web_summary(compact_summary, school["name"])
    open_attribute = " open" if open_by_default else ""
    return f"""
        <details class="day"{open_attribute}>
          <summary>
            <span class="day-name"><strong>{day_label}</strong><span>{date_label}</span></span>
            <span class="day-summary">{html.escape(compact_summary)}</span>
            <span class="chevron" aria-hidden="true"></span>
          </summary>
          <div class="day-details">
            {_menu_sections(menu_sections)}
            <a class="source-link" href="{html.escape(source_url)}" target="_blank" rel="noreferrer">View on Nutrislice</a>
          </div>
        </details>"""


def render_menu_page(
    schools: list[dict[str, str]],
    menus_by_school: dict[str, dict[dt.date, dict[str, list[str]]]],
    today: dt.date,
    generated_at: dt.datetime,
    summary_builder: Callable[[dict[str, str], dict[str, list[str]]], str],
) -> str:
    """Return a self-contained weekly menu and subscription page."""
    eligible_dates = displayed_menu_dates(today, generated_at)
    dates = [
        menu_date
        for menu_date in eligible_dates
        if any(
            has_menu(menus_by_school.get(school["slug"], {}).get(menu_date, {}))
            for school in schools
        )
    ]
    date_range_label = (
        format_date_range(dates[0], dates[-1])
        if dates
        else "No upcoming menus posted"
    )
    school_sections = []
    dialogs = []

    for school in schools:
        slug = school["slug"]
        name = school["name"]
        filename = f"{name.lower()}.ics"
        https_url = f"{PUBLIC_BASE_URL}/{filename}"
        webcal_url = https_url.replace("https://", "webcal://", 1)
        menus = menus_by_school.get(slug, {})
        school_dates = [
            menu_date for menu_date in dates if has_menu(menus.get(menu_date, {}))
        ]
        days = "".join(
            _day_card(
                school,
                menu_date,
                menus.get(menu_date, {}),
                summary_builder(school, menus.get(menu_date, {})),
                menu_date == school_dates[0],
            )
            for menu_date in school_dates
        )
        if not school_dates:
            days = '<p class="school-empty">No upcoming menus are posted.</p>'
        school_sections.append(
            f"""
      <section class="school" id="{html.escape(name.lower())}">
        <div class="school-heading">
          <div><p class="eyebrow">Lunch menu</p><h2>{html.escape(name)}</h2></div>
          <div class="subscribe-actions">
            <a class="button apple" href="{html.escape(webcal_url)}"> Add to Apple</a>
            <button class="button secondary" type="button" data-open-dialog="google-{html.escape(name.lower())}">Google / Android</button>
          </div>
        </div>
        <div class="days">{days}</div>
      </section>"""
        )
        dialogs.append(
            f"""
  <dialog id="google-{html.escape(name.lower())}" aria-labelledby="google-{html.escape(name.lower())}-title">
    <form method="dialog"><button class="dialog-close" aria-label="Close">×</button></form>
    <p class="eyebrow">{html.escape(name)} lunch menu</p>
    <h2 id="google-{html.escape(name.lower())}-title">Add to Google Calendar</h2>
    <p>Google adds calendar subscriptions from its website, not from the mobile app.</p>
    <ol>
      <li>Copy the calendar address below.</li>
      <li>On a computer, open Google Calendar and choose <strong>Other calendars → + → From URL</strong>.</li>
      <li>Paste the address and choose <strong>Add calendar</strong>. It will then sync to Android.</li>
    </ol>
    <div class="dialog-actions">
      <button class="button copy-button" type="button" data-copy-url="{html.escape(https_url)}">Copy calendar address</button>
      <a class="button secondary" href="{GOOGLE_ADD_URL}" target="_blank" rel="noreferrer">Open Google Calendar</a>
    </div>
    <code>{html.escape(https_url)}</code>
  </dialog>"""
        )

    generated_local = generated_at.astimezone(EASTERN_TIME)
    updated_label = generated_local.strftime("%b %d, %Y at %I:%M %p").replace(" 0", " ")
    favicon = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
        "%3Crect width='64' height='64' rx='14' fill='%231a3760'/%3E"
        "%3Ccircle cx='32' cy='32' r='17' fill='%23fff'/%3E"
        "%3Ccircle cx='32' cy='32' r='10' fill='%23ffb23f'/%3E%3C/svg%3E"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#18365f">
  <meta name="description" content="This week's Angier and Brown school lunch menus and calendar subscriptions.">
  <title>Newton school lunch menus</title>
  <link rel="icon" type="image/svg+xml" href="{favicon}">
  <style>
    :root {{ color-scheme: light; --ink:#14233b; --muted:#60708a; --blue:#18365f; --blue-2:#254d80; --orange:#ffb23f; --paper:#fff; --wash:#f2f5fa; --line:#dce3ed; }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; background:var(--wash); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; font-size:16px; line-height:1.45; }}
    a {{ color:inherit; }}
    .top {{ background:linear-gradient(135deg,var(--blue),var(--blue-2)); color:#fff; padding:.85rem max(1rem,calc((100vw - 70rem)/2)); }}
    .top-row {{ display:flex; align-items:center; justify-content:space-between; gap:.75rem; }}
    h1 {{ margin:0; font-size:clamp(1.35rem,4.5vw,2rem); line-height:1.08; letter-spacing:-.025em; }}
    .week {{ margin:.2rem 0 0; color:#d9e6f7; font-size:.88rem; }}
    .school-nav {{ display:flex; gap:.45rem; }}
    .school-nav a {{ padding:.38rem .62rem; border:1px solid #ffffff55; border-radius:999px; text-decoration:none; font-size:.82rem; font-weight:650; }}
    main {{ width:min(70rem,100%); margin:0 auto; padding:1rem; display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; align-items:start; }}
    .school {{ background:var(--paper); border:1px solid var(--line); border-radius:18px; overflow:hidden; box-shadow:0 10px 28px #243a5a0d; }}
    .school-heading {{ display:flex; align-items:center; justify-content:space-between; gap:.65rem; padding:.72rem .85rem; border-bottom:1px solid var(--line); }}
    .eyebrow {{ margin:0 0 .08rem; color:var(--muted); font-size:.68rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }}
    h2 {{ margin:0; font-size:1.28rem; line-height:1.05; }}
    .subscribe-actions {{ display:flex; flex-wrap:nowrap; justify-content:flex-end; gap:.35rem; }}
    .button {{ appearance:none; border:1px solid var(--blue); border-radius:9px; background:var(--blue); color:#fff; padding:.58rem .72rem; font:inherit; font-size:.82rem; font-weight:750; line-height:1.15; text-decoration:none; cursor:pointer; text-align:center; }}
    .button.secondary {{ background:#fff; color:var(--blue); }}
    .subscribe-actions .button {{ min-height:2.25rem; padding:.4rem .5rem; border-color:#cad5e4; background:#f7f9fc; color:#36577f; font-size:.75rem; font-weight:650; white-space:nowrap; }}
    .subscribe-actions .button:hover {{ border-color:#9cafc7; background:#eef3f8; color:var(--blue); }}
    .button:focus-visible, summary:focus-visible, .dialog-close:focus-visible {{ outline:3px solid var(--orange); outline-offset:2px; }}
    .days {{ padding:0 .55rem .65rem; }}
    .school-empty {{ margin:0; padding:1.25rem .5rem .7rem; color:var(--muted); }}
    .day {{ border-bottom:1px solid var(--line); }}
    .day:last-child {{ border-bottom:0; }}
    details.day summary {{ display:grid; grid-template-columns:5rem 1fr 1rem; gap:.75rem; align-items:center; min-height:4.35rem; padding:.7rem .5rem; cursor:pointer; list-style:none; }}
    details.day summary::-webkit-details-marker {{ display:none; }}
    .day-name {{ display:flex; flex-direction:column; line-height:1.25; }}
    .day-name strong {{ font-size:.91rem; }}
    .day-name span {{ color:var(--muted); font-size:.76rem; }}
    .day-summary {{ font-size:.93rem; }}
    .chevron {{ width:.55rem; height:.55rem; border-right:2px solid #718096; border-bottom:2px solid #718096; transform:rotate(45deg); transition:transform .16s ease; }}
    details[open] .chevron {{ transform:rotate(225deg); }}
    .day-details {{ margin:0 .45rem .75rem 5.75rem; padding:.8rem .9rem; border-left:3px solid var(--orange); background:#f7f9fc; border-radius:0 10px 10px 0; }}
    .menu-section + .menu-section {{ margin-top:.85rem; }}
    .menu-section h4 {{ margin:0 0 .28rem; font-size:.78rem; letter-spacing:.07em; text-transform:uppercase; color:var(--blue-2); }}
    .menu-section ul {{ margin:0; padding-left:1.15rem; }}
    .menu-section li {{ margin:.16rem 0; }}
    .source-link {{ display:inline-block; margin-top:.85rem; color:var(--blue-2); font-size:.82rem; font-weight:700; }}
    .day.empty {{ display:flex; align-items:center; justify-content:space-between; gap:1rem; min-height:4.35rem; padding:.7rem .5rem; }}
    .empty-label {{ color:var(--muted); font-size:.88rem; }}
    footer {{ width:min(70rem,100%); margin:0 auto; padding:.3rem 1rem 2rem; color:var(--muted); font-size:.78rem; }}
    dialog {{ width:min(31rem,calc(100% - 2rem)); border:0; border-radius:17px; padding:1.25rem; color:var(--ink); box-shadow:0 24px 70px #08172c55; }}
    dialog::backdrop {{ background:#0c1d35aa; backdrop-filter:blur(2px); }}
    dialog h2 {{ margin-bottom:.8rem; }}
    dialog p, dialog ol {{ color:#40516a; }}
    dialog ol {{ padding-left:1.3rem; }}
    dialog li + li {{ margin-top:.5rem; }}
    .dialog-close {{ float:right; border:0; background:transparent; color:var(--muted); font-size:1.7rem; line-height:1; cursor:pointer; }}
    .dialog-actions {{ display:flex; flex-wrap:wrap; gap:.55rem; margin:1rem 0; }}
    dialog code {{ display:block; overflow-wrap:anywhere; padding:.65rem; border-radius:8px; background:var(--wash); color:#40516a; font-size:.75rem; }}
    @media (max-width:760px) {{
      main {{ grid-template-columns:1fr; padding:.6rem; gap:.6rem; }}
    }}
    @media (max-width:420px) {{
      .top {{ padding:.72rem .75rem; }}
      .top-row {{ gap:.5rem; }}
      .school-nav {{ gap:.3rem; }}
      .school-nav a {{ padding:.32rem .48rem; }}
      .school-heading {{ padding:.65rem .7rem; }}
      .subscribe-actions {{ gap:.25rem; }}
      .subscribe-actions .button {{ padding:.36rem .4rem; font-size:.7rem; }}
      details.day summary {{ grid-template-columns:5.25rem 1fr .8rem; gap:.5rem; }}
      .day-details {{ margin:0 .25rem .75rem; }}
    }}
    @media (prefers-reduced-motion:reduce) {{ html {{ scroll-behavior:auto; }} .chevron {{ transition:none; }} }}
  </style>
</head>
<body>
  <header class="top">
    <div class="top-row">
      <div><h1>School lunch menus</h1><p class="week">{html.escape(date_range_label)}</p></div>
      <nav class="school-nav" aria-label="Schools"><a href="#angier">Angier</a><a href="#brown">Brown</a></nav>
    </div>
  </header>
  <main>{''.join(school_sections)}</main>
  <footer>Menus are provided by Newton Public Schools via Nutrislice. Updated {html.escape(updated_label)} ET.</footer>
  {''.join(dialogs)}
  <script>
    document.querySelectorAll('[data-open-dialog]').forEach(function(button) {{
      button.addEventListener('click', function() {{
        document.getElementById(button.dataset.openDialog).showModal();
      }});
    }});
    document.querySelectorAll('[data-copy-url]').forEach(function(button) {{
      button.addEventListener('click', async function() {{
        await navigator.clipboard.writeText(button.dataset.copyUrl);
        const original = button.textContent;
        button.textContent = 'Copied';
        setTimeout(function() {{ button.textContent = original; }}, 1800);
      }});
    }});
    document.querySelectorAll('dialog').forEach(function(dialog) {{
      dialog.addEventListener('click', function(event) {{
        if (event.target === dialog) dialog.close();
      }});
    }});
  </script>
</body>
</html>
"""
