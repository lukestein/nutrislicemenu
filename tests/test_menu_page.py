import datetime as dt
import unittest

from calendar_feed import event_summary
from menu_page import (
    displayed_menu_dates,
    format_date_range,
    format_web_summary,
    render_menu_page,
)


SCHOOLS = [
    {"district": "newtonk12", "name": "Angier", "slug": "angier-elementary"},
    {"district": "newtonk12", "name": "Brown", "slug": "brown-middle-school"},
]


class MenuPageTests(unittest.TestCase):
    def test_page_keeps_today_before_one_pm_eastern(self):
        self.assertEqual(
            displayed_menu_dates(
                dt.date(2026, 9, 14),
                dt.datetime(2026, 9, 14, 16, 59, tzinfo=dt.timezone.utc),
            ),
            [
                dt.date(2026, 9, 14),
                dt.date(2026, 9, 15),
                dt.date(2026, 9, 16),
                dt.date(2026, 9, 17),
                dt.date(2026, 9, 18),
                dt.date(2026, 9, 21),
            ],
        )

    def test_page_starts_with_tomorrow_at_one_pm_eastern(self):
        self.assertEqual(
            displayed_menu_dates(
                dt.date(2026, 9, 18),
                dt.datetime(2026, 9, 18, 17, 0, tzinfo=dt.timezone.utc),
            ),
            [
                dt.date(2026, 9, 21),
                dt.date(2026, 9, 22),
                dt.date(2026, 9, 23),
                dt.date(2026, 9, 24),
                dt.date(2026, 9, 25),
            ],
        )

    def test_date_range_handles_one_day_and_year_boundaries(self):
        self.assertEqual(
            format_date_range(dt.date(2026, 9, 14), dt.date(2026, 9, 14)),
            "September 14, 2026",
        )
        self.assertEqual(
            format_date_range(dt.date(2026, 12, 30), dt.date(2027, 1, 4)),
            "December 30, 2026–January 4, 2027",
        )

    def test_page_has_weekly_menus_and_subscription_actions(self):
        menus = {
            "angier-elementary": {
                dt.date(2026, 9, 14): {
                    "Lunch": ["Cheese Pizza", "Chicken Caesar Salad"]
                }
            },
            "brown-middle-school": {
                dt.date(2026, 9, 18): {"Create": ["Baked Falafel Flatbread"]}
            },
        }
        page = render_menu_page(
            SCHOOLS,
            menus,
            dt.date(2026, 9, 13),
            dt.datetime(2026, 9, 13, 18, 0, tzinfo=dt.timezone.utc),
            event_summary,
        )

        self.assertIn("September 14–18, 2026", page)
        self.assertNotIn("September 13–20, 2026", page)
        self.assertNotIn("Next 7 days", page)
        self.assertIn("Cheese pizza, chicken caesar salad", page)
        self.assertNotIn("cheese 🍕, chicken caesar 🥗", page)
        self.assertNotIn('<details class="day" open>', page)
        self.assertIn("Cheese Pizza", page)
        self.assertIn(
            "webcal://lukestein.com/nutrislicemenu/angier.ics", page
        )
        self.assertIn("Apple Calendar", page)
        self.assertIn("Google/Android", page)
        self.assertIn(
            'href="https://lukestein.com/nutrislicemenu/favicon.svg"', page
        )
        self.assertIn(
            'href="https://lukestein.com/nutrislicemenu/apple-touch-icon.png"',
            page,
        )
        self.assertNotIn("Angier: cheese", page)

    def test_page_has_clear_empty_state_when_no_menus_are_posted(self):
        page = render_menu_page(
            SCHOOLS,
            {school["slug"]: {} for school in SCHOOLS},
            dt.date(2026, 12, 24),
            dt.datetime(2026, 12, 24, 18, 0, tzinfo=dt.timezone.utc),
            event_summary,
        )

        self.assertIn("No upcoming menus posted", page)
        self.assertEqual(page.count("No upcoming menus are posted."), 2)
        self.assertNotIn("December 24–31, 2026", page)

    def test_single_school_page_has_simplified_header(self):
        menus = {
            "angier-elementary": {
                dt.date(2026, 9, 14): {"Lunch": ["Cheese Pizza"]}
            }
        }
        page = render_menu_page(
            SCHOOLS[:1],
            menus,
            dt.date(2026, 9, 14),
            dt.datetime(2026, 9, 14, 16, tzinfo=dt.timezone.utc),
            event_summary,
        )

        self.assertIn("<title>Angier lunch menu</title>", page)
        self.assertIn('<main class="single-school">', page)
        self.assertIn("<h1>Angier</h1>", page)
        self.assertNotIn('<nav class="school-nav"', page)
        self.assertNotIn("<h2>Angier</h2>", page)
        self.assertNotIn("Brown", page)

    def test_web_summary_uses_words_and_sentence_capitalization(self):
        self.assertEqual(
            format_web_summary(
                "Angier: 🌭, cheese 🍕, chicken caesar 🥗", "Angier"
            ),
            "Hot dog, cheese pizza, chicken caesar salad",
        )

    def test_page_escapes_menu_content(self):
        menus = {
            "angier-elementary": {
                dt.date(2026, 9, 14): {"Lunch": ["<script>alert(1)</script>"]}
            }
        }
        page = render_menu_page(
            SCHOOLS[:1],
            menus,
            dt.date(2026, 9, 14),
            dt.datetime(2026, 9, 14, 16, tzinfo=dt.timezone.utc),
            event_summary,
        )

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)


if __name__ == "__main__":
    unittest.main()
