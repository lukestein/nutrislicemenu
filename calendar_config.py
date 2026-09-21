"""Editable rules for compact calendar event summaries."""

# Matching is case-insensitive. Exact exclusions are useful for fixed offerings;
# regular expressions cover families of sides and condiments whose names vary.
COMMON_SUMMARY_EXCLUSION_PATTERNS = [
    r"\b(?:milk|sauce|dressing|packet|syrup|ranch)\b",
    r"\b(?:fries|tater tots|rice|tortilla chips)\b",
    r"^(?:assorted chilled|fresh whole|sliced fresh) fruit$",
    r"^(?:fresh |sliced |roasted |seasoned |shredded |marinated |red |green |"
    r"yellow |red and green )?"
    r"(?:broccoli florets|baby carrots?|carrots?|cucumbers?|grape tomatoes|"
    r"diced tomatoes|mixed vegetables|green beans|bell pepper strips|lettuce)$",
    r"^(?:peas and carrots|vegetarian baked beans|three bean salad|pea salad|"
    r"corn ranch salad|corn & black bean salad|spinach & romaine salad|"
    r"marinated tomato & cucumber salad)$",
    r"^(?:ketchup|mustard|salsa|sour cream)$",
    r"^(?:sliced fresh apples?|fresh .* apple)$",
    r"^(?:carrot & celery sticks|pickled red onion|(?:seasoned )?corn|"
    r"garbanzo beans|cuban style black beans)$",
    r"^(?:whole grain dinner roll|croutons?|(?:herb )?breadstick)$",
    r"^.*cucumbers?$",
]


SUMMARY_RULES = {
    "angier-elementary": {
        "exact": {
            "Breadstick",
            "Croutons",
            "Rotini Pasta",
            "Sunbutter & Grape Jelly Sandwich",
        },
        "patterns": [],
    },
    "brown-middle-school": {
        "exact": {
            # Daily 2Mato and Grill staples. Distinct vegetarian burgers have
            # appeared in the same recurring Grill slot on different weeks.
            "Classic Cheese Pizza",
            "Traditional Pepperoni Pizza",
            "Classic American Cheeseburger",
            "Veggie Burger",
            "Black Bean Burger",
            "Crispy Chicken Patty Sandwich",
            # Recurring On the Go offerings.
            "Crispy Chicken Caesar Salad",
            "Croutons",
            "Breadstick",
            "Mini Whole Grain Biscuit",
            "Penne Pasta",
            "Whole Grain Dinner Roll",
            "Turkey Ham & Cheese Sandwich",
            "Mixed Greens Salad with Cheese",
            "Turkey Chef Salad",
            "Creamy Chicken Caesar Wrap",
            "Buffalo Chicken Wrap",
            "Hummus, Chips, and Veggie Bento Box",
        },
        "patterns": [],
    },
}


# These substitutions shorten Nutrislice wording without affecting event bodies.
SUMMARY_ALIASES = {
    "Beef Hot Dog on Whole Wheat": "hot dog",
    "Jumbo Crispy Chicken Tenders": "crispy chicken tenders",
    "Whole Grain Waffle": "waffle",
    "Fish Taco in Soft Tortilla": "fish taco",
    "Italian Chicken Parm Sandwich": "chicken parm sandwich",
}


# Words that should remain capitalized when the surrounding title is lowercase.
SUMMARY_CAPITALIZATIONS = {
    "bbq": "BBQ",
    "blt": "BLT",
    "goldfish": "Goldfish",
    "pb&j": "PB&J",
}


SUMMARY_EMOJI_REPLACEMENTS = [
    (r"\b(?:beef )?hot dog(?: on whole wheat)?\b", "🌭"),
    (r"\bpizza\b", "🍕"),
    (r"\bsalad\b", "🥗"),
]
