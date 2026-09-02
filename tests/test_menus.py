import datetime as dt
import os
import unittest
from unittest.mock import Mock, patch

import nutrislicemenu
from menu_common import (
    HTTP_TIMEOUT_SECONDS,
    next_weekday,
    required_environment_variable,
    send_notification,
)


class DateTests(unittest.TestCase):
    def test_next_weekday(self):
        cases = {
            dt.date(2026, 9, 2): dt.date(2026, 9, 3),  # Wednesday
            dt.date(2026, 9, 4): dt.date(2026, 9, 7),  # Friday
            dt.date(2026, 9, 6): dt.date(2026, 9, 7),  # Sunday
        }
        for today, expected in cases.items():
            with self.subTest(today=today):
                self.assertEqual(next_weekday(today), expected)


class ConfigurationTests(unittest.TestCase):
    def test_required_environment_variable_rejects_missing_value(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "TEST_TOPIC"):
                required_environment_variable("TEST_TOPIC")


class NotificationTests(unittest.TestCase):
    @patch("menu_common.requests.post")
    def test_send_notification_checks_ntfy_response(self, post):
        response = Mock()
        post.return_value = response

        send_notification(
            topic_stub="private-topic",
            school_slug="example-school",
            message="- Pizza",
            title="Example menu",
            menu_url="https://example.com/menu",
        )

        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["timeout"], HTTP_TIMEOUT_SECONDS)
        response.raise_for_status.assert_called_once_with()


class NutrisliceTests(unittest.TestCase):
    @patch("nutrislicemenu.requests.get")
    def test_menu_parsing_filters_ignored_sections(self, get):
        response = Mock()
        response.json.return_value = {
            "days": [
                {
                    "date": "2026-09-03",
                    "menu_items": [
                        {"is_section_title": True, "text": "Lunch"},
                        {"food": {"name": "Turkey Sandwich"}},
                        {"is_section_title": True, "text": "Extra Extra"},
                        {"food": {"name": "Apple"}},
                    ],
                }
            ]
        }
        get.return_value = response

        menu = nutrislicemenu.get_menu_for_school(
            "district", "school", dt.date(2026, 9, 3)
        )

        self.assertEqual(menu, "- Turkey Sandwich")
        response.raise_for_status.assert_called_once_with()
        self.assertEqual(get.call_args.kwargs["timeout"], HTTP_TIMEOUT_SECONDS)

    @patch("nutrislicemenu.requests.get")
    def test_missing_day_returns_empty_menu(self, get):
        response = Mock()
        response.json.return_value = {"days": []}
        get.return_value = response

        menu = nutrislicemenu.get_menu_for_school(
            "district", "school", dt.date(2026, 9, 3)
        )

        self.assertEqual(menu, "")


if __name__ == "__main__":
    unittest.main()
