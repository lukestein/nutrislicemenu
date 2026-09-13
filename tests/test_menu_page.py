import datetime as dt
import unittest

from calendar_feed import event_summary
from menu_page import displayed_menu_dates, render_menu_page


SCHOOLS = [
    {"district": "newtonk12", "name": "Angier", "slug": "angier-elementary"},
    {"district": "newtonk12", "name": "Brown", "slug": "brown-middle-school"},
]


class MenuPageTests(unittest.TestCase):
    def test_page_displays_school_days_through_seven_days_ahead(self):
        self.assertEqual(
            displayed_menu_dates(dt.date(2026, 9, 13)),
            [
                dt.date(2026, 9, 14),
                dt.date(2026, 9, 15),
                dt.date(2026, 9, 16),
                dt.date(2026, 9, 17),
                dt.date(2026, 9, 18),
            ],
        )
        self.assertEqual(
            displayed_menu_dates(dt.date(2026, 9, 18)),
            [
                dt.date(2026, 9, 18),
                dt.date(2026, 9, 21),
                dt.date(2026, 9, 22),
                dt.date(2026, 9, 23),
                dt.date(2026, 9, 24),
                dt.date(2026, 9, 25),
            ],
        )

    def test_page_has_weekly_menus_and_subscription_actions(self):
        menus = {
            "angier-elementary": {
                dt.date(2026, 9, 14): {
                    "Lunch": ["Cheese Pizza", "Chicken Caesar Salad"]
                }
            },
            "brown-middle-school": {},
        }
        page = render_menu_page(
            SCHOOLS,
            menus,
            dt.date(2026, 9, 13),
            dt.datetime(2026, 9, 13, 18, 0, tzinfo=dt.timezone.utc),
            event_summary,
        )

        self.assertIn("Next 7 days · September 13–20, 2026", page)
        self.assertIn("cheese 🍕, chicken caesar 🥗", page)
        self.assertIn("Cheese Pizza", page)
        self.assertIn(
            "webcal://lukestein.com/nutrislicemenu/angier.ics", page
        )
        self.assertIn("Google / Android", page)
        self.assertIn("No menu posted", page)
        self.assertNotIn("Angier: cheese", page)

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
            dt.datetime(2026, 9, 14, tzinfo=dt.timezone.utc),
            event_summary,
        )

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)


if __name__ == "__main__":
    unittest.main()
