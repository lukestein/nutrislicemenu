import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import calendar_feed


ANGIER = {
    "district": "newtonk12",
    "name": "Angier",
    "slug": "angier-elementary",
}

BROWN = {
    "district": "newtonk12",
    "name": "Brown",
    "slug": "brown-middle-school",
}


class SummaryTests(unittest.TestCase):
    def test_angier_keeps_appealing_alternatives_but_hides_sunbutter(self):
        sections = {
            "Lunch": [
                "Cheese Pizza",
                "Fat Free Ranch, 0.4375 oz",
                "Fresh Broccoli Florets",
                "Sunbutter & Grape Jelly Sandwich",
                "Cheese Stuffed Breadsticks",
                "Chicken Caesar Salad",
            ]
        }

        self.assertEqual(
            calendar_feed.event_summary(ANGIER, sections),
            "Angier: Cheese 🍕, cheese stuffed breadsticks, chicken caesar 🥗",
        )

    def test_brown_removes_staples_but_keeps_rotating_station_items(self):
        sections = {
            "Create": ["Baked Falafel Flatbread", "Sliced Cucumbers"],
            "2Mato": ["Classic Cheese Pizza", "Margherita Pizza"],
            "Grill": [
                "Classic American Cheeseburger",
                "Beef Hot Dog on Whole Wheat",
                "Black Bean Burger",
                "BBQ Cheddar Chicken Sandwich",
                "Curly Fries",
            ],
        }

        self.assertEqual(
            calendar_feed.event_summary(BROWN, sections),
            "Brown: Baked falafel flatbread, margherita 🍕, "
            "🌭, BBQ cheddar chicken sandwich",
        )

    def test_summary_capitalizes_first_menu_item_for_each_school(self):
        sections = {
            "Lunch": ["Tempura Style Chicken Nuggets", "Jalapeno Carnita Pizza"]
        }

        self.assertEqual(
            calendar_feed.event_summary(BROWN, sections),
            "Brown: Tempura style chicken nuggets, jalapeno carnita 🍕",
        )
        self.assertEqual(
            calendar_feed.event_summary(ANGIER, sections),
            "Angier: Tempura style chicken nuggets, jalapeno carnita 🍕",
        )

    def test_compact_names_use_food_emoji(self):
        self.assertEqual(
            calendar_feed.compact_food_name("Beef Hot Dog on Whole Wheat"), "🌭"
        )
        self.assertEqual(
            calendar_feed.compact_food_name("Chicken Pizza Salad"),
            "chicken 🍕 🥗",
        )

    def test_summary_does_not_truncate_at_four_short_items(self):
        sections = {
            "Lunch": ["Tacos", "Pizza", "Pasta", "Panini", "Black Bean Burger"]
        }

        self.assertEqual(
            calendar_feed.event_summary(ANGIER, sections),
            "Angier: Tacos, 🍕, pasta, panini, black bean burger",
        )


class DescriptionTests(unittest.TestCase):
    def test_description_uses_notification_section_rules(self):
        description = calendar_feed.event_description(
            {
                "Lunch": ["Cheese Pizza"],
                "Extra Extra": ["Fresh Whole Fruit"],
                "Chef's Table": ["Chicken Caesar Salad"],
            },
            "https://example.com/menu",
        )

        self.assertEqual(
            description,
            "• Cheese Pizza\n\nChef's Table\n• Chicken Caesar Salad\n\n"
            "Nutrislice menu: https://example.com/menu",
        )


class CalendarTests(unittest.TestCase):
    def test_calendar_has_one_transparent_all_day_event_per_weekday_menu(self):
        generated_at = dt.datetime(2026, 9, 13, 15, 30, tzinfo=dt.timezone.utc)
        calendar = calendar_feed.serialize_calendar(
            ANGIER,
            {
                dt.date(2026, 9, 14): {"Lunch": ["Cheese Pizza"]},
                dt.date(2026, 9, 19): {"Lunch": ["Weekend Pizza"]},
                dt.date(2026, 9, 21): {},
            },
            generated_at,
        )

        self.assertEqual(calendar.count("BEGIN:VEVENT"), 1)
        self.assertIn(
            "UID:angier-elementary-20260914@nutrislicemenu.lukestein", calendar
        )
        self.assertIn("DTSTART;VALUE=DATE:20260914", calendar)
        self.assertIn("DTEND;VALUE=DATE:20260915", calendar)
        self.assertIn("X-WR-TIMEZONE:America/New_York", calendar)
        self.assertIn("TRANSP:TRANSPARENT", calendar)
        self.assertIn("SUMMARY:Angier: Cheese 🍕", calendar)
        self.assertNotIn("Weekend Pizza", calendar)
        self.assertTrue(calendar.endswith("END:VCALENDAR\r\n"))

    def test_calendar_escapes_text_and_folds_utf8_lines(self):
        generated_at = dt.datetime(2026, 9, 13, tzinfo=dt.timezone.utc)
        calendar = calendar_feed.serialize_calendar(
            ANGIER,
            {
                dt.date(2026, 9, 14): {
                    "Lunch": ["Entrée, with semicolon; and a very long café description"]
                }
            },
            generated_at,
        )

        self.assertIn("\\,", calendar)
        self.assertIn("\\;", calendar)
        for physical_line in calendar.split("\r\n"):
            self.assertLessEqual(len(physical_line.encode("utf-8")), 75)

    @patch("calendar_feed.get_menu_week")
    def test_generator_fetches_each_week_once_per_school(self, get_menu_week):
        get_menu_week.return_value = {}
        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = calendar_feed.generate_calendars(
                Path(temporary_directory),
                today=dt.date(2026, 9, 16),
                number_of_weeks=2,
            )

            self.assertEqual(get_menu_week.call_count, 4)
            self.assertEqual(
                {
                    str(path.relative_to(temporary_directory)) for path in paths
                },
                {
                    "angier.ics",
                    "brown.ics",
                    "index.html",
                    "favicon.svg",
                    "apple-touch-icon.png",
                    "angier/index.html",
                    "brown/index.html",
                },
            )
            self.assertTrue(all(path.exists() for path in paths))


if __name__ == "__main__":
    unittest.main()
