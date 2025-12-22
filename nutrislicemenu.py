import requests
import datetime
import sys
import os
from dotenv import load_dotenv

load_dotenv()

NTFY_TOPIC_STUB = os.getenv("NTFY_TOPIC_STUB", "nutrislicelunchmenu")

SCHOOLS = [
    {"name": "Angier", "slug": "angier-elementary"},
    {"name": "Brown", "slug": "brown-middle-school"},
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
def get_menu_for_school(school_slug, date_obj):
    # Use the .api subdomain which returns JSON data
    url = f"https://newtonk12.api.nutrislice.com/menu/api/weeks/school/{school_slug}/menu-type/lunch/{date_obj.year}/{date_obj.month}/{date_obj.day}/?format=json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"Error fetching menu: {e}"

    target_date_str = date_obj.strftime("%Y-%m-%d")
    
    # Find the specific day
    day_data = None
    for day in data.get('days', []):
        if day.get('date') == target_date_str:
            day_data = day
            break
            
    if not day_data or not day_data.get('menu_items'):
        return "No menu available."

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
        if item.get('station') and item['station'].get('name'):
            current_section = item['station']['name']

        if current_section not in menu_sections:
            menu_sections[current_section] = []
            
        menu_sections[current_section].append(food_name)

    # Format Markdown Output
    md_output = []
    
    # Force "General" to the bottom if it exists, otherwise sort alphabetically
    #sorted_sections = sorted(menu_sections.keys(), key=lambda x: (x == "General", x))
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
    # Calculate tomorrow
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%a %m/%d")
        
    for school in SCHOOLS:
        
        print(f"Trying {school['name']} for {tomorrow_str}...")
        try:
            
            full_message = ""
            #full_message += f"**Lunch Menu for {tomorrow_str}**\n"
            #full_message += f"\n---\n**{school['name']}**\n"
            full_message += get_menu_for_school(school['slug'], tomorrow) + "\n"
            
            menu_url = f"https://newtonk12.nutrislice.com/menu/{school['slug']}/lunch/{tomorrow.year}-{tomorrow.month}-{tomorrow.day}"
            
            if ("No menu available" not in full_message) and ("Error fetching menu" not in full_message):
                requests.post(f"https://ntfy.sh/{NTFY_TOPIC_STUB}-{school['slug']}",
                    data=full_message,
                    headers={
                        "Title": f"{school['name']} menu ({tomorrow_str})",
                        #"Priority": "urgent",
                        "Tags": "plate_with_cutlery",
                        "Markdown": "yes",
                        "Actions": f"view, Website, {menu_url}"
                    })
                
                print(f"Sending notification")

        except Exception as e:
            print(f"Failed to send: {e}")


if __name__ == "__main__":
    main()