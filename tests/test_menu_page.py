import datetime as dt
import unittest

from calendar_feed import event_summary
from menu_page import (
    displayed_menu_dates,
    format_date_range,
    format_web_summary,
    menu_dates_for_view,
    render_menu_page,
    week_menu_dates,
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

    def test_week_views_use_whole_monday_to_friday_weeks(self):
        generated_at = dt.datetime(2026, 9, 19, 18, tzinfo=dt.timezone.utc)
        self.assertEqual(
            week_menu_dates(dt.date(2026, 9, 16)),
            [dt.date(2026, 9, day) for day in range(14, 19)],
        )
        self.assertEqual(
            menu_dates_for_view(
                dt.date(2026, 9, 19), generated_at, "this-week"
            ),
            [dt.date(2026, 9, day) for day in range(21, 26)],
        )
        self.assertEqual(
            menu_dates_for_view(
                dt.date(2026, 9, 19), generated_at, "next-week"
            ),
            [
                dt.date(2026, 9, 28),
                dt.date(2026, 9, 29),
                dt.date(2026, 9, 30),
                dt.date(2026, 10, 1),
                dt.date(2026, 10, 2),
            ],
        )

    def test_page_week_views_show_only_the_selected_week(self):
        menus = {
            "angier-elementary": {
                dt.date(2026, 9, 18): {"Lunch": ["Old Week Meal"]},
                dt.date(2026, 9, 21): {"Lunch": ["This Week Meal"]},
                dt.date(2026, 9, 28): {"Lunch": ["Next Week Meal"]},
            }
        }
        generated_at = dt.datetime(2026, 9, 19, 18, tzinfo=dt.timezone.utc)
        this_week_page = render_menu_page(
            SCHOOLS[:1],
            menus,
            dt.date(2026, 9, 19),
            generated_at,
            event_summary,
            view="this-week",
        )
        self.assertIn("This week meal", this_week_page)
        self.assertNotIn("Old week meal", this_week_page)
        self.assertNotIn("Next week meal", this_week_page)
        self.assertIn('<strong aria-current="page">This week</strong>', this_week_page)
        self.assertIn(
            'href="https://lukestein.com/nutrislicemenu/angier/next-week/"',
            this_week_page,
        )

        next_week_page = render_menu_page(
            SCHOOLS,
            menus,
            dt.date(2026, 9, 19),
            generated_at,
            event_summary,
            view="next-week",
        )
        self.assertIn("Next week meal", next_week_page)
        self.assertNotIn("This week meal", next_week_page)
        self.assertIn('<strong aria-current="page">Next week</strong>', next_week_page)
        self.assertIn(
            'href="https://lukestein.com/nutrislicemenu/angier/next-week/"',
            next_week_page,
        )
        self.assertIn(
            ".school-nav, .school-actions, .week-views, .chevron, dialog, "
            ".source-link { display:none !important; }",
            next_week_page,
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
        self.assertIn(".school-nav { display:none;", page)
        self.assertIn(".school-nav { display:flex; }", page)
        self.assertIn(
            "@media (max-width:760px) {\n      html { font-size:18px; }", page
        )
        self.assertIn("Cheese pizza\u00a0· Chicken caesar salad", page)
        self.assertNotIn("cheese 🍕, chicken caesar 🥗", page)
        self.assertNotIn('<details class="day" open>', page)
        self.assertIn('<strong data-short="Mon">Monday</strong>', page)
        self.assertIn("Cheese Pizza", page)
        self.assertIn(
            "webcal://lukestein.com/nutrislicemenu/angier.ics", page
        )
        self.assertIn("Apple Calendar", page)
        self.assertIn("Google/Android", page)
        self.assertIn('title="Add to Apple Calendar"', page)
        self.assertIn('title="Add to Google or Android Calendar"', page)
        self.assertIn('class="visually-hidden">Apple Calendar</span>', page)
        self.assertEqual(page.count('class="button secondary expand-toggle"'), 2)
        self.assertIn('data-school-target="angier"', page)
        self.assertIn('data-school-target="brown"', page)
        self.assertIn('aria-label="Expand all menus"', page)
        self.assertIn("const shouldExpand = menus.some", page)
        self.assertIn("grid-auto-columns:2.35rem", page)
        self.assertIn(
            ".expand-toggle { border-color:transparent; background:transparent;",
            page,
        )
        self.assertIn(".chevron { justify-self:end;", page)
        self.assertIn("@media print {", page)
        self.assertIn(".day-name strong::after { content:none; }", page)
        self.assertIn("grid-template-columns:1in 1fr;", page)
        self.assertIn(
            ".school-nav, .school-actions, .week-views, .chevron, dialog, "
            ".source-link { display:none !important; }",
            page,
        )
        self.assertNotIn(">Upcoming<", page)
        self.assertIn('<strong aria-current="page">This week</strong>', page)
        self.assertIn(
            'href="https://lukestein.com/nutrislicemenu/next-week/">Next week</a>',
            page,
        )
        self.assertNotIn("View:", page)
        self.assertIn(
            ".week-views a { color:inherit; font-weight:500;", page
        )
        self.assertIn(
            ".week-views strong { color:var(--ink); font-weight:600;", page
        )
        self.assertIn("main:has(details[open]) { grid-template-columns:1fr; }", page)
        self.assertNotIn('<p class="eyebrow">Lunch menu</p>', page)
        self.assertIn("#angier { --school-accent:#2f68a0;", page)
        self.assertIn("#brown { --school-accent:#8a623f;", page)
        self.assertIn("background:var(--school-tint);", page)
        self.assertIn(
            '<h2><a class="school-page-link" '
            'href="https://lukestein.com/nutrislicemenu/angier/">Angier</a></h2>',
            page,
        )
        self.assertIn(
            '<h2><a class="school-page-link" '
            'href="https://lukestein.com/nutrislicemenu/brown/">Brown</a></h2>',
            page,
        )
        self.assertIn(
            ".school-page-link:hover, .school-page-link:focus-visible "
            "{ text-decoration:underline; }",
            page,
        )
        self.assertIn("content:attr(data-short);", page)
        self.assertIn("content:attr(data-short); font-size:1.1rem;", page)
        self.assertIn(
            'href="https://lukestein.com/nutrislicemenu/favicon.svg"', page
        )
        self.assertIn(
            'href="https://lukestein.com/nutrislicemenu/apple-touch-icon.png"',
            page,
        )
        self.assertNotIn("Angier: cheese", page)
        self.assertNotIn('<footer class="standalone-footer">', page)

    def test_upcoming_link_appears_when_it_differs_from_this_week(self):
        menus = {
            "angier-elementary": {
                dt.date(2026, 9, 14): {"Lunch": ["Monday Meal"]},
                dt.date(2026, 9, 21): {"Lunch": ["Following Monday Meal"]},
            }
        }
        generated_at = dt.datetime(2026, 9, 14, 16, tzinfo=dt.timezone.utc)
        upcoming_page = render_menu_page(
            SCHOOLS[:1],
            menus,
            dt.date(2026, 9, 14),
            generated_at,
            event_summary,
        )
        self.assertIn('<strong aria-current="page">Upcoming</strong>', upcoming_page)
        self.assertIn(
            'href="https://lukestein.com/nutrislicemenu/angier/this-week/">'
            "This week</a>",
            upcoming_page,
        )

        this_week_page = render_menu_page(
            SCHOOLS[:1],
            menus,
            dt.date(2026, 9, 14),
            generated_at,
            event_summary,
            view="this-week",
        )
        self.assertIn(
            'href="https://lukestein.com/nutrislicemenu/angier/">Upcoming</a>',
            this_week_page,
        )
        self.assertIn(
            '<strong aria-current="page">This week</strong>', this_week_page
        )

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
        self.assertNotIn('class="button secondary expand-toggle"', page)
        self.assertNotIn("December 24–31, 2026", page)

    def test_page_marks_new_week_after_holiday_gap(self):
        menus = {
            "angier-elementary": {
                dt.date(2026, 9, 16): {"Lunch": ["Cheese Pizza"]},
                dt.date(2026, 9, 22): {"Lunch": ["Chicken Tenders"]},
            }
        }
        page = render_menu_page(
            SCHOOLS[:1],
            menus,
            dt.date(2026, 9, 14),
            dt.datetime(2026, 9, 14, 17, tzinfo=dt.timezone.utc),
            event_summary,
        )

        self.assertEqual(page.count('<details class="day">'), 1)
        self.assertEqual(page.count('<details class="day week-break">'), 1)
        self.assertIn(
            ".day.week-break { margin-top:.55rem; border-top:3px solid", page
        )
        self.assertIn(".day:has(+ .day.week-break) { border-bottom:0; }", page)

    def test_brown_web_pages_show_posted_everyday_mains_but_angier_does_not(self):
        menus = {
            "brown-middle-school": {
                dt.date(2026, 9, 15): {
                    "2Mato": ["Classic Cheese Pizza", "Traditional Pepperoni Pizza"],
                    "Grill": [
                        "Classic American Cheeseburger",
                        "Veggie Burger",
                        "Crispy Chicken Patty Sandwich",
                    ],
                    "On the Go": [
                        "Crispy Chicken Caesar Salad",
                        "Turkey Ham & Cheese Sandwich",
                        "Creamy Chicken Caesar Wrap",
                        "Mixed Greens Salad with Cheese",
                        "Turkey Chef Salad",
                        "Buffalo Chicken Wrap",
                        "Hummus, Chips, and Veggie Bento Box",
                    ],
                },
                dt.date(2026, 9, 16): {
                    "2Mato": ["Classic Cheese Pizza", "Traditional Pepperoni Pizza"],
                    "Grill": [
                        "Classic American Cheeseburger",
                        "Black Bean Burger",
                        "Crispy Chicken Patty Sandwich",
                    ],
                    "On the Go": [
                        "Crispy Chicken Caesar Salad",
                        "Turkey Ham & Cheese Sandwich",
                        "Creamy Chicken Caesar Wrap",
                        "Mixed Greens Salad with Cheese",
                        "Turkey Chef Salad",
                        "Buffalo Chicken Wrap",
                        "Hummus, Chips, and Veggie Bento Box",
                    ],
                },
            },
            "angier-elementary": {
                dt.date(2026, 9, 15): {"Lunch": ["Cheese Pizza"]},
            },
        }
        for schools in (SCHOOLS, SCHOOLS[1:]):
            with self.subTest(schools=[school["name"] for school in schools]):
                page = render_menu_page(
                    schools,
                    menus,
                    dt.date(2026, 9, 15),
                    dt.datetime(2026, 9, 15, 16, tzinfo=dt.timezone.utc),
                    event_summary,
                )
                self.assertEqual(page.count('<div class="everyday-footer">'), 1)
                self.assertIn(
                    "Cheese pizza\u00a0· Pepperoni pizza\u00a0· Cheeseburger"
                    "\u00a0· Veggie/<wbr>black bean burger\u00a0· Crispy chicken patty sandwich",
                    page,
                )
                self.assertIn("Pizza\u00a0&amp; grill", page)
                self.assertIn("On the go", page)
                self.assertIn(
                    "Crispy chicken Caesar salad\u00a0· Turkey ham\u00a0&amp; cheese sandwich"
                    "\u00a0· Creamy chicken Caesar wrap\u00a0· Mixed greens salad with cheese"
                    "\u00a0· Turkey chef salad\u00a0· Buffalo chicken wrap"
                    "\u00a0· Hummus, chips\u00a0&amp; veggie bento box",
                    page,
                )
                self.assertEqual(page.count("<wbr>"), 1)
                self.assertNotIn("Veggie/ black bean burger", page)
                self.assertIn(
                    ".days:has(+ .everyday-footer) { padding-bottom:0; }", page
                )
                self.assertIn(
                    ".everyday-footer { grid-template-columns:1in 1fr;", page
                )
                self.assertIn("background:var(--school-tint);", page)
                self.assertNotIn(".day:has(+ .day.everyday)", page)
                self.assertIn(
                    ".everyday-footer .day-name strong { font-size:1.1rem; }", page
                )
                self.assertIn(
                    ".everyday-footer .day-name strong { font-size:10pt; }", page
                )
                self.assertIn('.everyday-group-label { display:inline-block;', page)
                self.assertNotIn('<details class="day everyday">', page)

        angier_page = render_menu_page(
            SCHOOLS[:1],
            menus,
            dt.date(2026, 9, 15),
            dt.datetime(2026, 9, 15, 16, tzinfo=dt.timezone.utc),
            event_summary,
        )
        self.assertNotIn('<div class="everyday-footer">', angier_page)

    def test_brown_everyday_row_requires_multiple_days_and_each_item_on_all_days(self):
        first_day = dt.date(2026, 9, 15)
        second_day = dt.date(2026, 9, 16)
        menus = {
            "brown-middle-school": {
                first_day: {
                    "2Mato": ["Classic Cheese Pizza", "Traditional Pepperoni Pizza"],
                    "Grill": ["Classic American Cheeseburger"],
                },
            }
        }
        generated_at = dt.datetime(2026, 9, 15, 16, tzinfo=dt.timezone.utc)
        one_day_page = render_menu_page(
            SCHOOLS[1:], menus, first_day, generated_at, event_summary
        )
        self.assertNotIn('<div class="everyday-footer">', one_day_page)

        menus["brown-middle-school"][second_day] = {
            "2Mato": ["Classic Cheese Pizza"],
            "Grill": ["Classic American Cheeseburger"],
        }
        two_day_page = render_menu_page(
            SCHOOLS[1:], menus, first_day, generated_at, event_summary
        )
        self.assertIn('<div class="everyday-footer">', two_day_page)
        self.assertIn("Cheese pizza\u00a0· Cheeseburger", two_day_page)
        self.assertNotIn("Pepperoni pizza\u00a0· Cheeseburger", two_day_page)

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
        self.assertIn('<header class="top standalone-top">', page)
        self.assertIn('<div class="top-row standalone-top-row">', page)
        self.assertIn('<footer class="standalone-footer">', page)
        self.assertIn(
            ".standalone-footer { width:min(38rem,calc(100% - 1.2rem)); }",
            page,
        )
        self.assertIn(
            ".standalone-top-row { width:min(38rem,100%); margin:0 auto; "
            "padding-right:.15rem; }",
            page,
        )
        self.assertEqual(page.count('class="button secondary expand-toggle"'), 1)
        self.assertIn('data-school-target="angier"', page)
        self.assertNotIn('<nav class="school-nav"', page)
        self.assertNotIn("<h2>Angier</h2>", page)
        self.assertNotIn('class="school-page-link"', page)
        self.assertNotIn("Brown", page)

    def test_web_summary_uses_words_and_sentence_capitalization(self):
        self.assertEqual(
            format_web_summary(
                "Angier: 🌭\u00a0· cheese 🍕\u00a0· chicken caesar 🥗", "Angier"
            ),
            "Hot dog\u00a0· cheese pizza\u00a0· chicken caesar salad",
        )
        self.assertEqual(
            format_web_summary(
                "Brown: Tempura style chicken nuggets\u00a0· "
                "Jalapeno carnita 🍕\u00a0· 🌭",
                "Brown",
            ),
            "Tempura style chicken nuggets\u00a0· Jalapeno carnita pizza\u00a0· "
            "Hot dog",
        )

    def test_web_headers_keep_ampersands_with_the_previous_word(self):
        menu_date = dt.date(2026, 9, 14)
        page = render_menu_page(
            SCHOOLS,
            {
                "angier-elementary": {
                    menu_date: {"Lunch": ["Muffin, Goldfish & Yogurt Fun Lunch"]}
                },
                "brown-middle-school": {
                    menu_date: {"Create": ["Citrus Kidney & Garbanzo Bean Salad"]}
                },
            },
            dt.date(2026, 9, 13),
            dt.datetime(2026, 9, 13, 18, tzinfo=dt.timezone.utc),
            event_summary,
        )
        self.assertIn("Muffin, Goldfish\u00a0&amp; yogurt fun lunch", page)
        self.assertIn("Citrus kidney\u00a0&amp; garbanzo bean salad", page)

    def test_page_escapes_menu_content(self):
        menus = {
            "angier-elementary": {
                dt.date(2026, 9, 14): {
                    "Chef's Table": ["Meat Lover's <script>alert(1)</script>"]
                }
            }
        }
        page = render_menu_page(
            SCHOOLS[:1],
            menus,
            dt.date(2026, 9, 14),
            dt.datetime(2026, 9, 14, 16, tzinfo=dt.timezone.utc),
            event_summary,
        )

        self.assertIn("Chef’s Table", page)
        self.assertIn("Meat Lover’s &lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)

    def test_brown_expanded_details_hide_condiments(self):
        menu_date = dt.date(2026, 9, 14)
        generated_at = dt.datetime(2026, 9, 14, 16, tzinfo=dt.timezone.utc)
        foods = [
            "Beef Hot Dog on Whole Wheat",
            "Ketchup Packet",
            "Ranch Dressing",
            "Creamy Caesar Dressing",
            "General Tso Sauce",
        ]
        brown_page = render_menu_page(
            SCHOOLS[1:],
            {
                "brown-middle-school": {
                    menu_date: {
                        "2Mato": ["Classic Cheese Pizza"],
                        "Grill": foods,
                    }
                }
            },
            menu_date,
            generated_at,
            event_summary,
        )
        self.assertIn("<h4>Pizza</h4>", brown_page)
        self.assertNotIn("<h4>2Mato</h4>", brown_page)
        self.assertIn("Beef Hot Dog on Whole Wheat", brown_page)
        self.assertIn("General Tso Sauce", brown_page)
        self.assertNotIn("Ketchup Packet", brown_page)
        self.assertNotIn("Ranch Dressing", brown_page)
        self.assertNotIn("Creamy Caesar Dressing", brown_page)

        angier_page = render_menu_page(
            SCHOOLS[:1],
            {"angier-elementary": {menu_date: {"Lunch": foods}}},
            menu_date,
            generated_at,
            event_summary,
        )
        self.assertIn("Ketchup Packet", angier_page)
        self.assertIn("Ranch Dressing", angier_page)


if __name__ == "__main__":
    unittest.main()
