import datetime as dt

import requests
from dotenv import load_dotenv

from menu_common import (
    HTTP_TIMEOUT_SECONDS,
    next_weekday,
    required_environment_variable,
    send_notification,
)

load_dotenv()

SCHOOLS = [
    {"district": "newtonk12", "name": "Angier", "slug": "angier-elementary"},
    {"district": "newtonk12", "name": "Brown", "slug": "brown-middle-school"},
]

IGNORED_SECTIONS = [
    "Milk & Condiments",
    "Extra Extra",
    "So Deli",
    "On the Go",
]

HIDE_SECTION_HEADERS = [
    "Lunch",
    "Create",
]

# --- SCRIPT ---
def get_menu_for_school(district: str, school_slug: str, date_obj: dt.date) -> str:
    # Use the .api subdomain which returns JSON data
    url = f"https://{district}.api.nutrislice.com/menu/api/weeks/school/{school_slug}/menu-type/lunch/{date_obj.year}/{date_obj.month}/{date_obj.day}/?format=json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Nutrislice returned an unexpected response")

    target_date_str = date_obj.strftime("%Y-%m-%d")
    
    # Find the specific day
    day_data = None
    for day in data.get('days', []):
        if day.get('date') == target_date_str:
            day_data = day
            break
            
    if not day_data or not day_data.get('menu_items'):
        return ""

    menu_sections = {}
    current_section = "General" # Default if no header is found
    
    # Nutrislice often returns a flat list where a "Header" item is followed by "Food" items
    for item in day_data.get('menu_items', []):
        
        # 1. Check if this item is actually a Section Header
        # "is_section_title" is the standard flag, but sometimes it's just a text field with no food
        if item.get('is_section_title') is True or (item.get('text') and not item.get('food')):
            raw_section = item.get('text', '') or item.get('name', '')
            if raw_section:
                current_section = raw_section
            continue

        # 2. Skip spacer items or images without food
        if not item.get('food'): 
            continue
        
        food_name = item['food'].get('name')
        if not food_name: 
            continue

        # 3. Double Check: specific station metadata might override the list position
        # If the item explicitly says it belongs to a station, use that.
        station = item.get("station") or {}
        if station.get("name"):
            current_section = station["name"]

        if current_section not in menu_sections:
            menu_sections[current_section] = []
            
        menu_sections[current_section].append(food_name)

    # Format Markdown Output
    md_output = []
    
    sorted_sections = [s for s in menu_sections.keys() if s not in IGNORED_SECTIONS]
    
    for section in sorted_sections:
        section_md_output = []
        if section not in HIDE_SECTION_HEADERS:
            section_md_output.append(f"**{section}**")
        for food in menu_sections[section]:
            section_md_output.append(f"- {food}")
            
        md_output.append("\n".join(section_md_output))
    
    return "\n\n".join(md_output)


def main():
    topic_stub = required_environment_variable("NTFY_TOPIC_STUB")
    menu_date = next_weekday()
    menu_date_str = menu_date.strftime("%a %m/%d")
    failures = []
        
    for school in SCHOOLS:
        print(f"Trying {school['name']} for {menu_date_str}...")
        try:
            message = get_menu_for_school(
                school["district"], school["slug"], menu_date
            )
            if not message:
                print("No menu available; skipping notification")
                continue

            menu_url = (
                f"https://{school['district']}.nutrislice.com/menu/"
                f"{school['slug']}/lunch/{menu_date.isoformat()}"
            )
            send_notification(
                topic_stub=topic_stub,
                school_slug=school["slug"],
                message=message,
                title=f"{school['name']} menu ({menu_date_str})",
                menu_url=menu_url,
            )
            print("Notification sent")
        except Exception as exc:
            failures.append(f"{school['name']}: {exc}")
            print(f"Failed: {exc}")

    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    main()
