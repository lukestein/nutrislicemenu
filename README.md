A small tool to send a push notification with the next school day's lunch menu.

Uses GitHub Actions and [ntfy](https://ntfy.sh/). During the school year,
notifications run at 6:17 PM America/New_York time on Sunday through Thursday,
including across daylight saving time changes. July and August are skipped.

Set `NTFY_TOPIC_STUB` as a GitHub Actions secret or local environment variable.
It is required so the script cannot accidentally publish to a predictable
default ntfy topic.
