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
    def test_angier_keeps_recurring_main_alternatives(self):
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
            "Angier menu: cheese pizza, sunbutter & grape jelly sandwich, "
            "cheese stuffed breadsticks, chicken caesar salad",
        )

    def test_brown_removes_staples_but_keeps_rotating_station_items(self):
        sections = {
            "Create": ["Baked Falafel Flatbread", "Sliced Cucumbers"],
            "2Mato": ["Classic Cheese Pizza", "Margherita Pizza"],
            "Grill": [
                "Classic American Cheeseburger",
                "BBQ Cheddar Chicken Sandwich",
                "Curly Fries",
            ],
        }

        self.assertEqual(
            calendar_feed.event_summary(BROWN, sections),
            "Brown menu: baked falafel flatbread, margherita pizza, "
            "BBQ cheddar chicken sandwich",
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
        self.assertIn("TRANSP:TRANSPARENT", calendar)
        self.assertIn("SUMMARY:Angier menu: cheese pizza", calendar)
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
            self.assertEqual({path.name for path in paths}, {"angier.ics", "brown.ics"})
            self.assertTrue(all(path.exists() for path in paths))


if __name__ == "__main__":
    unittest.main()
