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
            "Angier: Cheese 🍕\u00a0· Cheese stuffed breadsticks\u00a0· "
            "Chicken caesar 🥗",
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
            "Brown: Baked falafel flatbread\u00a0· Margherita 🍕\u00a0· "
            "🌭\u00a0· BBQ cheddar chicken sandwich",
        )

    def test_brown_summary_removes_generic_sides_from_headlines(self):
        sections = {
            "Create": [
                "Crispy Baked Tofu",
                "General Tso Sauce",
                "Brown Rice",
                "Roasted Green Beans",
            ],
            "2Mato": [
                "Classic Cheese Pizza",
                "Traditional Pepperoni Pizza",
                "Margherita Pizza",
            ],
            "Grill": [
                "Classic American Cheeseburger",
                "Black Bean Burger",
                "Crispy Chicken Patty Sandwich",
                "BBQ Cheddar Chicken Sandwich",
            ],
            "Extra Extra": ["Garbanzo Beans", "Corn", "Herb Breadstick"],
        }

        expected = (
            "Brown: Crispy baked tofu\u00a0· Margherita 🍕\u00a0· "
            "BBQ cheddar chicken sandwich"
        )
        self.assertEqual(calendar_feed.event_summary(BROWN, sections), expected)
        self.assertEqual(calendar_feed.web_summary(BROWN, sections), expected)

    def test_web_headline_is_not_limited_to_calendar_title_length(self):
        sections = {
            "Create": [
                "Spaghetti with Chicken Meatballs",
                "Baked Falafel Flatbread",
                "Tempura Style Chicken Nuggets",
                "Nashville Hot Chicken Sandwich",
                "Cheese & Roasted Vegetable Panini",
            ]
        }

        calendar_title = calendar_feed.event_summary(BROWN, sections)
        web_headline = calendar_feed.web_summary(BROWN, sections)
        self.assertTrue(calendar_title.endswith("\u00a0· …"))
        self.assertNotIn("Cheese\u00a0& roasted vegetable panini", calendar_title)
        self.assertIn("Cheese\u00a0& roasted vegetable panini", web_headline)
        self.assertNotIn("…", web_headline)

    def test_summary_capitalizes_each_menu_item_for_each_school(self):
        sections = {
            "Lunch": ["Tempura Style Chicken Nuggets", "Jalapeno Carnita Pizza"]
        }

        self.assertEqual(
            calendar_feed.event_summary(BROWN, sections),
            "Brown: Tempura style chicken nuggets\u00a0· Jalapeno carnita 🍕",
        )
        self.assertEqual(
            calendar_feed.event_summary(ANGIER, sections),
            "Angier: Tempura style chicken nuggets\u00a0· Jalapeno carnita 🍕",
        )

    def test_compact_names_use_food_emoji(self):
        self.assertEqual(
            calendar_feed.compact_food_name("Beef Hot Dog on Whole Wheat"), "🌭"
        )
        self.assertEqual(
            calendar_feed.compact_food_name("Chicken Pizza Salad"),
            "chicken 🍕 🥗",
        )
        self.assertEqual(
            calendar_feed.compact_food_name("Meat Lover's Pizza"),
            "meat lover’s 🍕",
        )
        self.assertEqual(
            calendar_feed.compact_food_name(
                "Muffin, Goldfish & Yogurt Fun Lunch"
            ),
            "muffin, Goldfish\u00a0& yogurt fun lunch",
        )
        self.assertEqual(
            calendar_feed.event_summary(
                ANGIER,
                {"Lunch": ["Muffin, Goldfish & Yogurt Fun Lunch"]},
            ),
            "Angier: Muffin, Goldfish\u00a0& yogurt fun lunch",
        )

    def test_ampersand_stays_with_previous_word_in_compact_titles(self):
        self.assertEqual(
            calendar_feed.event_summary(
                BROWN,
                {"Create": ["Citrus Kidney & Garbanzo Bean Salad"]},
            ),
            "Brown: Citrus kidney\u00a0& garbanzo bean 🥗",
        )

    def test_summary_does_not_truncate_at_four_short_items(self):
        sections = {
            "Lunch": ["Tacos", "Pizza", "Pasta", "Panini", "Black Bean Burger"]
        }

        self.assertEqual(
            calendar_feed.event_summary(ANGIER, sections),
            "Angier: Tacos\u00a0· 🍕\u00a0· Pasta\u00a0· Panini\u00a0· "
            "Black bean burger",
        )


class DescriptionTests(unittest.TestCase):
    def test_description_uses_notification_section_rules(self):
        description = calendar_feed.event_description(
            {
                "Lunch": ["Cheese Pizza"],
                "Extra Extra": ["Fresh Whole Fruit"],
                "Chef's Table": ["Farmer's Chicken Salad"],
            },
            "https://example.com/menu",
        )

        self.assertEqual(
            description,
            "• Cheese Pizza\n\nChef’s Table\n• Farmer’s Chicken Salad\n\n"
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
                    "this-week/index.html",
                    "next-week/index.html",
                    "favicon.svg",
                    "apple-touch-icon.png",
                    "angier/index.html",
                    "angier/this-week/index.html",
                    "angier/next-week/index.html",
                    "brown/index.html",
                    "brown/this-week/index.html",
                    "brown/next-week/index.html",
                },
            )
            self.assertTrue(all(path.exists() for path in paths))


if __name__ == "__main__":
    unittest.main()
