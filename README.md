A small tool to send a push notification with the next school day's lunch menu.

Uses GitHub Actions and [ntfy](https://ntfy.sh/). During the school year,
notifications run at 6:17 PM America/New_York time on Sunday through Thursday,
including across daylight saving time changes. July and August are skipped.

Set `NTFY_TOPIC_STUB` as a GitHub Actions secret or local environment variable.
It is required so the script cannot accidentally publish to a predictable
default ntfy topic.

## Calendar feeds

The repository also generates separate public, read-only iCalendar feeds for
Angier and Brown. Each school day with a published menu becomes one transparent
all-day event. Event titles contain a compact selection of the day's main
choices, while event descriptions contain the sectioned menu and a link to
Nutrislice.

The Pages site at <https://lukestein.com/nutrislicemenu/> shows the next seven
days of school menus in a fast, phone-friendly format and provides subscription
instructions for Apple Calendar, Google Calendar, and Android.

The `Publish Lunch Menu Calendars` workflow deploys the generated files as this
repository's own GitHub Pages artifact. It does not commit to or modify the
`lukestein.github.io` repository. Once GitHub Pages is enabled with **GitHub
Actions** as its source, the subscription URLs are:

- <https://lukestein.com/nutrislicemenu/angier.ics>
- <https://lukestein.com/nutrislicemenu/brown.ics>

Compact-title exclusions and aliases are intentionally kept in
`calendar_config.py` so they can be tuned as Nutrislice item names change.
