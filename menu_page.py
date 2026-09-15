"""Render the fast, static web page published with the calendar feeds."""

from __future__ import annotations

import datetime as dt
import html
from collections.abc import Callable

from menu_common import EASTERN_TIME, typographic_text
from nutrislicemenu import HIDE_SECTION_HEADERS, IGNORED_SECTIONS


PUBLIC_BASE_URL = "https://lukestein.com/nutrislicemenu"
GOOGLE_ADD_URL = "https://calendar.google.com/calendar/u/0/r/settings/addbyurl"
WEB_SUMMARY_REPLACEMENTS = {
    "🌭": "Hot dog",
    "🍕": "pizza",
    "🥗": "salad",
}
MENU_DAY_ROLLOVER_HOUR = 13
# Web-only labels for Brown's recurring 2Mato and Grill mains. An item is shown
# in the "Every day" row only if one of its posted names occurs on every
# displayed Brown menu day; the vegetarian burger changes names by week.
BROWN_EVERYDAY_MAINS = (
    ("Cheese pizza", "2Mato", ("Classic Cheese Pizza",)),
    ("Pepperoni pizza", "2Mato", ("Traditional Pepperoni Pizza",)),
    ("Cheeseburger", "Grill", ("Classic American Cheeseburger",)),
    ("Veggie burger", "Grill", ("Veggie Burger", "Black Bean Burger")),
    ("Crispy chicken patty sandwich", "Grill", ("Crispy Chicken Patty Sandwich",)),
)


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
            heading = f'<h4>{html.escape(typographic_text(section))}</h4>'
        items = "".join(
            f"<li>{html.escape(typographic_text(food))}</li>" for food in foods
        )
        blocks.append(f'<div class="menu-section">{heading}<ul>{items}</ul></div>')
    return "".join(blocks)


def _day_card(
    school: dict[str, str],
    menu_date: dt.date,
    menu_sections: dict[str, list[str]],
    compact_summary: str,
    starts_new_week: bool = False,
) -> str:
    day_label = menu_date.strftime("%A")
    date_label = f"{menu_date:%b} {menu_date.day}"
    day_classes = "day week-break" if starts_new_week else "day"
    source_url = (
        f"https://{school['district']}.nutrislice.com/menu/"
        f"{school['slug']}/lunch/{menu_date.isoformat()}"
    )
    if not has_menu(menu_sections):
        return f"""
        <div class="{day_classes} empty">
          <div class="day-name"><strong data-short="{menu_date:%a}">{day_label}</strong><span>{date_label}</span></div>
          <span class="empty-label">No menu posted</span>
        </div>"""

    compact_summary = format_web_summary(compact_summary, school["name"])
    return f"""
        <details class="{day_classes}">
          <summary>
            <span class="day-name"><strong data-short="{menu_date:%a}">{day_label}</strong><span>{date_label}</span></span>
            <span class="day-summary">{html.escape(compact_summary)}</span>
            <span class="chevron" aria-hidden="true"></span>
          </summary>
          <div class="day-details">
            {_menu_sections(menu_sections)}
            <a class="source-link" href="{html.escape(source_url)}" target="_blank" rel="noreferrer">View on Nutrislice</a>
          </div>
        </details>"""


def _brown_everyday_footer(
    school_dates: list[dt.date],
    menus: dict[dt.date, dict[str, list[str]]],
) -> str:
    """Show only Brown mains posted on every day in the visible window."""
    if len(school_dates) < 2:
        return ""
    labels = []
    for label, section, names in BROWN_EVERYDAY_MAINS:
        possible_names = {name.casefold() for name in names}
        if all(
            possible_names.intersection(
                food.casefold() for food in menus[menu_date].get(section, [])
            )
            for menu_date in school_dates
        ):
            labels.append(label)
    if not labels:
        return ""
    summary = html.escape("\u00a0· ".join(labels))
    return f"""
        <div class="everyday-footer">
          <span class="day-name"><strong>Every day</strong></span>
          <span class="day-summary">{summary}</span>
        </div>"""


def render_menu_page(
    schools: list[dict[str, str]],
    menus_by_school: dict[str, dict[dt.date, dict[str, list[str]]]],
    today: dt.date,
    generated_at: dt.datetime,
    summary_builder: Callable[[dict[str, str], dict[str, list[str]]], str],
) -> str:
    """Return a self-contained weekly menu and subscription page."""
    standalone_school = schools[0] if len(schools) == 1 else None
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
    header_actions = ""

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
                starts_new_week=(
                    index > 0
                    and menu_date.isocalendar()[:2]
                    != school_dates[index - 1].isocalendar()[:2]
                ),
            )
            for index, menu_date in enumerate(school_dates)
        )
        everyday_footer = (
            _brown_everyday_footer(school_dates, menus)
            if slug == "brown-middle-school"
            else ""
        )
        if not school_dates:
            days = '<p class="school-empty">No upcoming menus are posted.</p>'
        expand_action = ""
        if school_dates:
            expand_action = f"""
            <button class="button secondary expand-toggle" type="button" data-school-target="{html.escape(name.lower())}" aria-expanded="false" aria-label="Expand all menus" title="Expand all menus">
              <svg aria-hidden="true" viewBox="0 0 24 24"><path d="m7 5 5 5 5-5M7 12l5 5 5-5"/></svg>
              <span class="visually-hidden">Expand all menus</span>
            </button>"""
        school_actions = f"""
          <div class="school-actions">
            <a class="button apple" href="{html.escape(webcal_url)}" title="Add to Apple Calendar">
              <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701"/></svg>
              <span class="visually-hidden">Apple Calendar</span>
            </a>
            <button class="button secondary google-calendar" type="button" data-open-dialog="google-{html.escape(name.lower())}" title="Add to Google or Android Calendar">
              <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M18.316 5.684H24v12.632h-5.684V5.684zM5.684 24h12.632v-5.684H5.684V24zM18.316 5.684V0H1.895A1.894 1.894 0 0 0 0 1.895v16.421h5.684V5.684h12.632zm-7.207 6.25v-.065c.272-.144.5-.349.687-.617s.279-.595.279-.982c0-.379-.099-.72-.3-1.025a2.05 2.05 0 0 0-.832-.714 2.703 2.703 0 0 0-1.197-.257c-.6 0-1.094.156-1.481.467-.386.311-.65.671-.793 1.078l1.085.452c.086-.249.224-.461.413-.633.189-.172.445-.257.767-.257.33 0 .602.088.816.264a.86.86 0 0 1 .322.703c0 .33-.12.589-.36.778-.24.19-.535.284-.886.284h-.567v1.085h.633c.407 0 .748.109 1.02.327.272.218.407.499.407.843 0 .336-.129.614-.387.832s-.565.327-.924.327c-.351 0-.651-.103-.897-.311-.248-.208-.422-.502-.521-.881l-1.096.452c.178.616.505 1.082.977 1.401.472.319.984.478 1.538.477a2.84 2.84 0 0 0 1.293-.291c.382-.193.684-.458.902-.794.218-.336.327-.72.327-1.149 0-.429-.115-.797-.344-1.105a2.067 2.067 0 0 0-.881-.689zm2.093-1.931l.602.913L15 10.045v5.744h1.187V8.446h-.827l-2.158 1.557zM22.105 0h-3.289v5.184H24V1.895A1.894 1.894 0 0 0 22.105 0zm-3.289 23.5l4.684-4.684h-4.684V23.5zM0 22.105C0 23.152.848 24 1.895 24h3.289v-5.184H0v3.289z"/></svg>
              <span class="visually-hidden">Google/Android</span>
            </button>
            {expand_action}
          </div>"""
        school_heading = ""
        if standalone_school:
            header_actions = school_actions
        else:
            school_page_url = f"{PUBLIC_BASE_URL}/{name.lower()}/"
            school_heading = f"""
        <div class="school-heading">
          <h2><a class="school-page-link" href="{html.escape(school_page_url)}">{html.escape(name)}</a></h2>
          {school_actions}
        </div>"""
        school_sections.append(
            f"""
      <section class="school" id="{html.escape(name.lower())}">
        {school_heading}
        <div class="days">{days}</div>
        {everyday_footer}
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
    if standalone_school:
        school_name = standalone_school["name"]
        document_title = f"{school_name} lunch menu"
        description = f"Upcoming {school_name} school lunch menus and calendar subscription."
        header_content = f"""
      <div><p class="eyebrow top-eyebrow">Lunch menu</p><h1>{html.escape(school_name)}</h1><p class="week">{html.escape(date_range_label)}</p></div>
      {header_actions}"""
        main_class = ' class="single-school"'
        footer_class = ' class="standalone-footer"'
        top_class = "top standalone-top"
        top_row_class = "top-row standalone-top-row"
    else:
        document_title = "Newton school lunch menus"
        description = "Upcoming Angier and Brown school lunch menus and calendar subscriptions."
        header_content = f"""
      <div><h1>School lunch menus</h1><p class="week">{html.escape(date_range_label)}</p></div>
      <nav class="school-nav" aria-label="Schools"><a href="#angier">Angier</a><a href="#brown">Brown</a></nav>"""
        main_class = ""
        footer_class = ""
        top_class = "top"
        top_row_class = "top-row"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#18365f">
  <meta name="description" content="{html.escape(description)}">
  <title>{html.escape(document_title)}</title>
  <link rel="icon" type="image/svg+xml" href="{PUBLIC_BASE_URL}/favicon.svg">
  <link rel="apple-touch-icon" sizes="180x180" href="{PUBLIC_BASE_URL}/apple-touch-icon.png">
  <style>
    :root {{ color-scheme: light; --ink:#14233b; --muted:#60708a; --blue:#18365f; --blue-2:#254d80; --orange:#ffb23f; --paper:#fff; --wash:#f2f5fa; --line:#dce3ed; }}
    * {{ box-sizing:border-box; }}
    .visually-hidden {{ position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; background:var(--wash); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; font-size:16px; line-height:1.45; }}
    a {{ color:inherit; }}
    .top {{ background:linear-gradient(135deg,var(--blue),var(--blue-2)); color:#fff; padding:.85rem max(1rem,calc((100vw - 70rem)/2)); }}
    .top-row {{ display:flex; align-items:center; justify-content:space-between; gap:.75rem; }}
    .standalone-top-row {{ width:min(38rem,100%); margin:0 auto; padding-right:.15rem; }}
    h1 {{ margin:0; font-size:clamp(1.35rem,4.5vw,2rem); line-height:1.08; letter-spacing:-.025em; }}
    .week {{ margin:.2rem 0 0; color:#d9e6f7; font-size:.88rem; }}
    .top-eyebrow {{ color:#bcd0e9; }}
    .school-nav {{ display:none; gap:.45rem; }}
    .school-nav a {{ padding:.38rem .62rem; border:1px solid #ffffff55; border-radius:999px; text-decoration:none; font-size:.82rem; font-weight:650; }}
    main {{ width:min(70rem,100%); margin:0 auto; padding:1rem; display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; align-items:start; }}
    main.single-school {{ grid-template-columns:minmax(0,38rem); justify-content:center; }}
    .school {{ background:var(--paper); border:1px solid var(--line); border-radius:18px; overflow:hidden; box-shadow:0 10px 28px #243a5a0d; }}
    #angier {{ --school-accent:#2f68a0; --school-tint:#eef5fc; }}
    #brown {{ --school-accent:#8a623f; --school-tint:#f7f0e8; }}
    .school-heading {{ display:flex; align-items:center; justify-content:space-between; gap:.65rem; padding:.72rem .15rem .72rem .85rem; border-top:3px solid var(--school-accent); border-bottom:1px solid var(--line); background:var(--school-tint); }}
    .eyebrow {{ margin:0 0 .08rem; color:var(--muted); font-size:.68rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }}
    h2 {{ margin:0; font-size:1.28rem; line-height:1.05; }}
    .school-page-link {{ color:inherit; text-decoration:none; text-underline-offset:.16em; }}
    .school-page-link:hover, .school-page-link:focus-visible {{ text-decoration:underline; }}
    .school-actions {{ display:grid; grid-auto-flow:column; grid-auto-columns:2.35rem; flex:0 0 auto; width:auto; gap:.3rem; }}
    .button {{ appearance:none; border:1px solid var(--blue); border-radius:9px; background:var(--blue); color:#fff; padding:.58rem .72rem; font:inherit; font-size:.82rem; font-weight:750; line-height:1.15; text-decoration:none; cursor:pointer; text-align:center; }}
    .button.secondary {{ background:#fff; color:var(--blue); }}
    .school-actions .button {{ display:flex; align-items:center; justify-content:center; width:2.35rem; min-width:2.35rem; height:2.35rem; min-height:2.35rem; padding:.55rem; border-color:#cad5e4; background:#ffffff99; color:#36577f; }}
    .school-actions .button svg {{ display:block; width:100%; height:100%; fill:currentColor; }}
    .school-actions .google-calendar {{ color:#4285f4; }}
    .school-actions .expand-toggle {{ border-color:transparent; background:transparent; color:#60708a; }}
    .school-actions .expand-toggle svg {{ fill:none; stroke:currentColor; stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round; transition:transform .16s ease; }}
    .school-actions .expand-toggle[aria-expanded="true"] svg {{ transform:rotate(180deg); }}
    .school-actions .button:hover {{ border-color:#9cafc7; background:#eef3f8; color:var(--blue); }}
    .top .school-actions .button {{ border-color:#ffffff55; background:#ffffff12; color:#fff; }}
    .top .school-actions .button:hover {{ border-color:#ffffff88; background:#ffffff20; color:#fff; }}
    .top .school-actions .expand-toggle {{ border-color:transparent; background:transparent; }}
    .button:focus-visible, .school-page-link:focus-visible, summary:focus-visible, .dialog-close:focus-visible {{ outline:3px solid var(--orange); outline-offset:2px; }}
    .days {{ padding:0 .55rem .65rem; }}
    .days:has(+ .everyday-footer) {{ padding-bottom:0; }}
    .school-empty {{ margin:0; padding:1.25rem .5rem .7rem; color:var(--muted); }}
    .day {{ border-bottom:1px solid var(--line); }}
    .day:has(+ .day.week-break) {{ border-bottom:0; }}
    .day.week-break {{ margin-top:.55rem; border-top:3px solid var(--school-accent,var(--blue-2)); }}
    .everyday-footer {{ display:grid; grid-template-columns:5rem 1fr; gap:.75rem; align-items:center; min-height:4rem; padding:.8rem 1.1rem; background:var(--school-tint); }}
    .day:last-child {{ border-bottom:0; }}
    details.day summary {{ display:grid; grid-template-columns:5rem 1fr 1rem; gap:.75rem; align-items:center; min-height:4.35rem; padding:.7rem .5rem; cursor:pointer; list-style:none; }}
    details.day summary::-webkit-details-marker {{ display:none; }}
    .day-name {{ display:flex; flex-direction:column; line-height:1.25; }}
    .day-name strong {{ font-size:.91rem; }}
    .day-name span {{ color:var(--muted); font-size:.76rem; }}
    .day-summary {{ font-size:.93rem; }}
    .chevron {{ justify-self:end; width:.55rem; height:.55rem; border-right:2px solid #718096; border-bottom:2px solid #718096; transform:rotate(45deg); transition:transform .16s ease; }}
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
    .standalone-footer {{ width:min(38rem,calc(100% - 1.2rem)); }}
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
      html {{ font-size:18px; }}
      .top.standalone-top {{ padding-left:.6rem; padding-right:.6rem; }}
      main {{ grid-template-columns:1fr; padding:.6rem; gap:.6rem; }}
      .school-nav {{ display:flex; }}
      details.day summary {{ grid-template-columns:4rem 1fr .9rem; gap:.55rem; min-height:4.6rem; padding:.78rem .5rem; }}
      .everyday-footer {{ grid-template-columns:4rem 1fr; gap:.55rem; min-height:4.2rem; padding:.78rem 1.1rem; }}
      .day-name strong {{ font-size:0; }}
      .day-name strong::after {{ content:attr(data-short); font-size:1.1rem; }}
      .everyday-footer .day-name strong {{ font-size:1.1rem; }}
      .day-name span {{ font-size:.82rem; }}
      .day-summary {{ font-size:1rem; line-height:1.42; }}
      .empty-label {{ font-size:.94rem; }}
      footer {{ font-size:.84rem; }}
    }}
    @media (max-width:420px) {{
      .top {{ padding:.72rem .75rem; }}
      .top-row {{ gap:.5rem; }}
      .school-nav {{ gap:.3rem; }}
      .school-nav a {{ padding:.34rem .5rem; font-size:.84rem; }}
      .school-heading {{ padding:.65rem .15rem .65rem .7rem; }}
      .school-actions {{ gap:.25rem; }}
      .school-actions .button {{ padding:.4rem; font-size:.82rem; }}
      .day-details {{ margin:0 .25rem .75rem; }}
    }}
    @media print {{
      @page {{ size:letter portrait; margin:.4in; }}
      :root {{ --ink:#000; --muted:#333; --paper:#fff; --wash:#fff; --line:#777; }}
      html, body {{ background:#fff; color:#000; font-size:10pt; }}
      body {{ line-height:1.3; }}
      .top {{ background:none; color:#000; padding:0 0 .12in; border-bottom:2pt solid #000; }}
      .top-row {{ align-items:flex-end; }}
      h1 {{ font-size:20pt; letter-spacing:-.015em; }}
      .week, .top-eyebrow, .eyebrow {{ color:#000; }}
      .week {{ font-size:10pt; }}
      .school-nav, .school-actions, .chevron, dialog, .source-link {{ display:none !important; }}
      main {{ width:100%; margin:0; padding:.18in 0 0; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.18in; align-items:start; }}
      main.single-school {{ grid-template-columns:1fr; }}
      .school {{ border:1pt solid #555; border-radius:0; box-shadow:none; overflow:visible; }}
      .school-heading {{ padding:.1in .12in; border-top:3pt solid #000; border-bottom:1pt solid #555; background:#fff; }}
      h2 {{ font-size:15pt; }}
      .days {{ padding:0 .1in .08in; }}
      .days:has(+ .everyday-footer) {{ padding-bottom:0; }}
      .day {{ border-bottom:.6pt solid #999; break-inside:avoid; }}
      .day.week-break {{ margin-top:.08in; border-top:2pt solid #000; }}
      .everyday-footer {{ grid-template-columns:1in 1fr; gap:.08in; min-height:0; padding:.08in .14in; border-top:1pt solid #555; background:#eee; break-inside:avoid; print-color-adjust:exact; }}
      details.day summary {{ grid-template-columns:1in 1fr; gap:.08in; min-height:0; padding:.08in .04in; cursor:default; }}
      .day-name strong {{ font-size:10pt; }}
      .everyday-footer .day-name strong {{ font-size:10pt; }}
      .day-name strong::after {{ content:none; }}
      .day-name span {{ color:#222; font-size:8.5pt; }}
      .day-summary {{ font-size:9.5pt; line-height:1.28; }}
      details.day[open] summary {{ display:block; padding-bottom:.04in; }}
      details.day[open] .day-name {{ flex-direction:row; align-items:baseline; gap:.08in; }}
      details.day[open] .day-summary {{ display:none; }}
      details.day[open] .day-details {{ display:block !important; }}
      .day-details {{ margin:0; padding:.02in .12in .09in; border:0; border-left:2pt solid #555; background:#fff; border-radius:0; }}
      .menu-section + .menu-section {{ margin-top:.07in; }}
      .menu-section h4 {{ margin-bottom:.02in; color:#000; font-size:8pt; }}
      .menu-section ul {{ padding-left:.16in; }}
      .menu-section li {{ margin:0; font-size:9pt; }}
      .day.empty {{ min-height:0; padding:.08in .04in; }}
      .empty-label {{ color:#222; font-size:9pt; }}
      footer, .standalone-footer {{ width:100%; padding:.15in 0 0; color:#222; font-size:8pt; break-inside:avoid; }}
      main:has(details[open]) {{ grid-template-columns:1fr; }}
      main:has(details[open]) .school {{ break-after:page; }}
      main:has(details[open]) .school:last-child {{ break-after:auto; }}
    }}
    @media (prefers-reduced-motion:reduce) {{ html {{ scroll-behavior:auto; }} .chevron, .expand-toggle svg {{ transition:none; }} }}
  </style>
</head>
<body>
  <header class="{top_class}">
    <div class="{top_row_class}">
      {header_content}
    </div>
  </header>
  <main{main_class}>{''.join(school_sections)}</main>
  <footer{footer_class}>Menus are provided by Newton Public Schools via Nutrislice. Updated {html.escape(updated_label)} ET.</footer>
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
    document.querySelectorAll('[data-school-target]').forEach(function(button) {{
      const school = document.getElementById(button.dataset.schoolTarget);
      const menus = Array.from(school.querySelectorAll('details.day'));
      const label = button.querySelector('.visually-hidden');
      function updateToggle() {{
        const allExpanded = menus.length > 0 && menus.every(function(menu) {{ return menu.open; }});
        const action = allExpanded ? 'Collapse all menus' : 'Expand all menus';
        button.setAttribute('aria-expanded', String(allExpanded));
        button.setAttribute('aria-label', action);
        button.title = action;
        label.textContent = action;
      }}
      button.addEventListener('click', function() {{
        const shouldExpand = menus.some(function(menu) {{ return !menu.open; }});
        menus.forEach(function(menu) {{ menu.open = shouldExpand; }});
        updateToggle();
      }});
      menus.forEach(function(menu) {{ menu.addEventListener('toggle', updateToggle); }});
      updateToggle();
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
