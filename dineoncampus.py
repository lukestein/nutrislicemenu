import requests
import datetime
import sys
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

NTFY_TOPIC_STUB = os.getenv("NTFY_TOPIC_STUB_DOC", "dineoncampuslunchmenu")

SCHOOLS = [
    {"location": "babson", "name": "Trim Dining Hall", "slug": "trim-dining-hall"},
]

IGNORED_SECTIONS = [
    "Condiments",
    "Beverages",
    "Milk",
]

HIDE_SECTION_HEADERS = []

# Text length filters for menu items
MIN_ITEM_LENGTH = 10
MAX_ITEM_LENGTH = 100
MAX_HEADER_LENGTH = 50

# --- SCRIPT ---
def get_menu_for_school(location, school_slug, date_obj):
    # Build the URL for the Dine On Campus page
    url = f"https://new.dineoncampus.com/{location}/whats-on-the-menu/{school_slug}/{date_obj.year}-{date_obj.month:02d}-{date_obj.day:02d}/lunch"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        return f"Error fetching menu: {e}"

    # Parse the HTML
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
    except Exception as e:
        return f"Error parsing menu: {e}"

    menu_sections = {}
    
    # Find all station/section elements
    # Dine On Campus typically uses divs or sections with specific classes
    # Look for station headers and menu items
    
    # Common patterns:
    # 1. Look for station names (section headers)
    # 2. Look for menu items under each station
    
    # Try to find stations - these vary by site but common patterns include:
    # - Elements with class containing 'station'
    # - Headers followed by menu items
    # - Structured divs containing station name and items
    
    # Strategy 1: Look for elements that might be station containers
    def is_station_class(classes):
        """Check if any class suggests this is a station container."""
        if not classes:
            return False
        # Convert to lowercase once for efficiency
        classes_lower = ' '.join(classes).lower()
        return 'station' in classes_lower or 'menu' in classes_lower
    
    station_containers = soup.find_all(['div', 'section'], class_=is_station_class)
    
    if not station_containers:
        # Strategy 2: Look for common heading tags that might be station names
        # followed by lists or divs containing menu items
        current_section = "General"
        
        # Find all potential headers and items
        for element in soup.find_all(['h2', 'h3', 'h4', 'div', 'li']):
            # Check if this could be a section header
            if element.name in ['h2', 'h3', 'h4']:
                section_text = element.get_text(strip=True)
                if section_text and len(section_text) < MAX_HEADER_LENGTH:  # Headers are usually short
                    current_section = section_text
                    continue
            
            # Check if element has class suggesting it's a menu item
            classes = element.get('class', [])
            # Preprocess classes for efficiency
            class_strings = [str(c).lower() for c in classes]
            if any(keyword in cls for cls in class_strings for keyword in ['item', 'dish', 'food']):
                item_text = element.get_text(strip=True)
                if item_text and len(item_text) > 0:
                    if current_section not in menu_sections:
                        menu_sections[current_section] = []
                    menu_sections[current_section].append(item_text)
    else:
        # Parse station containers
        for container in station_containers:
            # Find station name
            station_name = None
            station_header = container.find(['h2', 'h3', 'h4', 'div'], class_=lambda x: x and 'name' in x.lower())
            if station_header:
                station_name = station_header.get_text(strip=True)
            
            if not station_name:
                # Try data attributes
                station_name = container.get('data-station-name') or container.get('data-name')
            
            if not station_name:
                station_name = "General"
            
            # Find menu items in this container
            items = container.find_all(['div', 'li'], class_=lambda x: x and ('item' in x.lower() or 'dish' in x.lower()))
            
            if not items:
                # Try finding all text-containing elements
                items = container.find_all(['div', 'span', 'li'])
            
            if station_name not in menu_sections:
                menu_sections[station_name] = []
            
            for item in items:
                item_text = item.get_text(strip=True)
                # Filter out empty or very long text (likely descriptions)
                if item_text and MIN_ITEM_LENGTH < len(item_text) < MAX_ITEM_LENGTH:
                    # Clean up the text
                    item_text = item_text.split('\n')[0]  # Take first line if multi-line
                    if item_text not in menu_sections[station_name]:
                        menu_sections[station_name].append(item_text)
    
    # If we didn't find any sections with our parsing, try a simpler approach
    if not menu_sections:
        # Look for any text that might be menu items
        all_text_elements = soup.find_all(text=True)
        for text in all_text_elements:
            text = text.strip()
            # Filter for reasonable menu item lengths
            if text and MIN_ITEM_LENGTH < len(text) < MAX_ITEM_LENGTH and not text.startswith('<'):
                if "General" not in menu_sections:
                    menu_sections["General"] = []
                menu_sections["General"].append(text)
    
    if not menu_sections:
        return "No menu available."

    # Format Markdown Output
    md_output = []
    
    sorted_sections = [s for s in menu_sections.keys() if s not in IGNORED_SECTIONS]
    
    for section in sorted_sections:
        if not menu_sections[section]:  # Skip empty sections
            continue
            
        section_md_output = []
        if section not in HIDE_SECTION_HEADERS:
            section_md_output.append(f"**{section}**")
        for food in menu_sections[section]:
            section_md_output.append(f"- {food}")
            
        md_output.append("\n".join(section_md_output))
    
    if not md_output:
        return "No menu available."
    
    return "\n\n".join(md_output)


def main():
    # Calculate tomorrow (or next weekday if tomorrow is weekend)
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    
    # If tomorrow is Saturday (5) or Sunday (6), find next Monday
    while tomorrow.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        tomorrow += datetime.timedelta(days=1)
    
    tomorrow_str = tomorrow.strftime("%a %m/%d")
        
    for school in SCHOOLS:
        
        print(f"Trying {school['name']} for {tomorrow_str}...")
        try:
            
            full_message = ""
            full_message += get_menu_for_school(school['location'],
                                                school['slug'],
                                                tomorrow) + "\n"
            
            menu_url = f"https://new.dineoncampus.com/{school['location']}/whats-on-the-menu/{school['slug']}/{tomorrow.year}-{tomorrow.month:02d}-{tomorrow.day:02d}/lunch"
            
            if ("No menu available" not in full_message) and ("Error fetching menu" not in full_message):
                requests.post(f"https://ntfy.sh/{NTFY_TOPIC_STUB}-{school['slug']}",
                    data=full_message,
                    headers={
                        "Title": f"{school['name']} menu ({tomorrow_str})",
                        "Tags": "plate_with_cutlery",
                        "Markdown": "yes",
                        "Actions": f"view, Website, {menu_url}"
                    })
                
                print(f"Sending notification")
            else:
                print(f"Skipping notification: {full_message[:100]}")

        except Exception as e:
            print(f"Failed to send: {e}")


if __name__ == "__main__":
    main()
