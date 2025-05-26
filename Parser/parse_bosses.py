import requests
import mwparserfromhell
from collections import defaultdict
import os
import re

# Map enum keys to a list of section title aliases (all lowercase)
SECTION_ALIASES = {
    "ALWAYS": ["100%", "frozen tears", "ancient shards"],
    "SUPPLIES": ["supplies", "potions", "consumables", "secondary supply roll", "minor drops"],
    "WEAPONSANDARMOUR": ["weapons and armour", "weapons", "armour", "staves"],
    "RUNESANDAMMUNITION": ["runes and ammunition", "runes", "ammunition", "elemental runes", "catalytic runes", "combination runes"],
    "MATERIALS": ["materials", "herbs", "seeds", "ores and bars", "fish", "fishing", "bolt tips", "resources", "noted herbs", "food", "talismans", "talismans (noted)", "gemstones", "dragonhide", "fletching materials", "tree-herb seed drop table"],
    "OTHER": ["other", "gloves", "jewellery", "junk"],
    "TERTIARY": ["tertiary", "ancient statuettes", "secondary"],
    "UNIQUE": ["unique", "uniques", "pre-roll", "sigils", "mutagens", "secondary uniques"]
}

IGNORE_ITEMS = {"Nothing", "Coins"}

DROP_TABLE_TEMPLATES = {
    "AllotmentSeedDropLines": [
        "Potato seed", "Onion seed", "Cabbage seed", "Tomato seed", "Sweetcorn seed",
        "Strawberry seed", "Watermelon seed"
    ],
    "FossilDropLines": [
        "Small fossil", "Medium fossil", "Large fossil", "Rare fossil"
    ],
    "GeneralSeedDropLines": [
        "Guam seed", "Marrentill seed", "Tarromin seed", "Harralander seed", "Ranarr seed",
        "Irit seed", "Avantoe seed", "Kwuarm seed", "Cadantine seed", "Lantadyme seed",
        "Dwarf weed seed", "Belladonna seed", "Watermelon seed", "Strawberry seed",
        "Wildblood seed", "Jangerberry seed", "Whiteberry seed", "Poison ivy seed",
        "Toadflax seed", "Snapdragon seed", "Mushroom spore", "Cactus seed", "Potato cactus seed"
    ],
    "HerbDropLines": [
        "Grimy guam leaf", "Grimy marrentill", "Grimy tarromin", "Grimy harralander",
        "Grimy ranarr weed", "Grimy irit leaf", "Grimy avantoe", "Grimy kwuarm",
        "Grimy cadantine", "Grimy lantadyme", "Grimy dwarf weed"
    ],
    "RareSeedDropLines": [
        "Torstol seed", "Spirit seed", "Celastrus seed", "Redwood tree seed", "Dragonfruit tree seed",
        "Hespori seed", "White lily seed"
    ],
    "TalismanDropLines": [
        "Air talisman", "Mind talisman", "Water talisman", "Earth talisman", "Fire talisman",
        "Body talisman", "Cosmic talisman", "Chaos talisman", "Nature talisman", "Law talisman",
        "Death talisman", "Blood talisman", "Soul talisman"
    ],
    "TreeHerbSeedDropLines": [
        "Acorn", "Willow seed", "Maple seed", "Yew seed", "Magic seed",
        "Apple tree seed", "Banana tree seed", "Orange tree seed", "Curry tree seed",
        "Pineapple seed", "Papaya tree seed", "Palm tree seed", "Calquat tree seed"
    ],
    "UncommonSeedDropLines": [
        "Guam seed", "Marrentill seed", "Tarromin seed", "Harralander seed", "Ranarr seed",
        "Irit seed", "Avantoe seed", "Kwuarm seed", "Cadantine seed", "Lantadyme seed",
        "Dwarf weed seed", "Belladonna seed", "Watermelon seed", "Strawberry seed",
        "Wildblood seed", "Jangerberry seed", "Whiteberry seed", "Poison ivy seed",
        "Toadflax seed", "Snapdragon seed", "Mushroom spore", "Cactus seed", "Potato cactus seed"
    ],
    "UsefulHerbDropLines": [
        "Grimy ranarr weed", "Grimy irit leaf", "Grimy avantoe", "Grimy kwuarm",
        "Grimy cadantine", "Grimy lantadyme", "Grimy dwarf weed", "Grimy torstol"
    ]
}

HARDCODED_LOCATIONS = {
    "ZULRAH": {
        "coords": [[2260,3066,0,2277,3081,0]],  # Note the double brackets for consistency
        "name": "Zulrah Shrine",
        "template": (
            "#define CONST_AREA_ZULRAH0 [2260,3066,0,2277,3081,0] // [[Zulrah Shrine]]\n"
            "#define CONST_ZULRAH_RULE(_cond) rule ((area:CONST_AREA_ZULRAH0) && (_cond))"
        )
    },
    "YAMA": {
        "coords": [[1475,10053,1,1528,10106,1]],
        "name": "Chasm of Fire",
        "template": (
            "#define CONST_AREA_YAMA0 [1475,10053,1,1528,10106,1] // [[Chasm of Fire]]\n"
            "#define CONST_YAMA_RULE(_cond) rule ((area:CONST_AREA_YAMA0) && (_cond))"
        )
    },
    "NEX": {
        "coords": [[2910,5187,0,2944,5219,0]],
        "name": "Ancient Prison",
        "template": (
            "#define CONST_AREA_NEX0 [2910,5187,0,2944,5219,0] // [[Ancient Prison]]\n"
            "#define CONST_NEX_RULE(_cond) rule ((area:CONST_AREA_NEX0) && (_cond))"
        )
    },
    "GROTESQUE_GUARDIANS": {
        "coords": [[1671,4549,0,1724,4603,0]],
        "name": "Slayer Tower Rooftop",
        "template": (
            "#define CONST_AREA_GROTESQUE_GUARDIANS0 [1671,4549,0,1724,4603,0] // [[Slayer Tower Rooftop]]\n"
            "#define CONST_GROTESQUE_GUARDIANS_RULE(_cond) rule ((area:CONST_AREA_GROTESQUE_GUARDIANS0) && (_cond))"
        )
    }
}

def map_section_to_enum(section_title):
    section_title = section_title.lower().strip()
    for enum_key, aliases in SECTION_ALIASES.items():
        if section_title in aliases:
            return enum_key
    return None

def get_wikitext(page_title):
    url = "https://oldschool.runescape.wiki/api.php"
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "wikitext",
        "format": "json"
    }
    headers = {"User-Agent": "DropParserBot/1.0"}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()['parse']['wikitext']['*']

def extract_items_from_nodes(nodes):
    IGNORE_ITEMS = {"Nothing", "Coins"}
    items = set()
    for node in nodes:
        if hasattr(node, 'filter_wikilinks'):
            for link in node.filter_wikilinks():
                item_name = str(link.title).strip()
                if item_name and item_name not in IGNORE_ITEMS:
                    items.add(item_name)
        if isinstance(node, mwparserfromhell.nodes.Template):
            template_name = str(node.name).strip()
            if template_name in DROP_TABLE_TEMPLATES:
                items.update(DROP_TABLE_TEMPLATES[template_name])
            for param in ['item', 'name', 'drop']:
                if node.has(param):
                    val = node.get(param).value.strip_code().strip()
                    if val and val not in IGNORE_ITEMS:
                        items.add(val)
    return items

def extract_categorized_drops(wikitext):
    code = mwparserfromhell.parse(wikitext)
    categorized_drops = defaultdict(set)

    current_section = None
    section_nodes = []

    for node in code.nodes:
        if isinstance(node, mwparserfromhell.nodes.Heading):
            if current_section:
                items = extract_items_from_nodes(section_nodes)
                categorized_drops[current_section].update(items)
            section_nodes = []
            current_section = map_section_to_enum(node.title.strip())
            print(f"DEBUG: Section heading '{node.title.strip()}' mapped to enum '{current_section}'")
        else:
            if current_section:
                section_nodes.append(node)

    if current_section:
        items = extract_items_from_nodes(section_nodes)
        categorized_drops[current_section].update(items)

    # Remove empty categories and sort
    categorized_drops = {k: sorted(v) for k, v in categorized_drops.items() if v}

    print(f"DEBUG: Extracted categorized drops: {categorized_drops}")
    return categorized_drops

def format_enum_block(items):
    if not items:
        return "[]"
    return "[" + ", ".join(f'"{item}"' for item in items) + "]"

def remove_empty_sections(filled, enum_keys):
    for key in enum_keys:
        # Regex to match section between START_KEY and END_KEY including the markers
        pattern = re.compile(
            rf"// START_{key}\n.*?__{key}_ENUM__.*?// END_{key}\n?",
            re.DOTALL | re.IGNORECASE
        )
        filled = pattern.sub("", filled)
    return filled

def fill_code_template(monster_name, drop_categories, template_text, locations_text=None):
    # Remove apostrophes from both display name and variable names
    monster_display = monster_name.replace("'", "")
    monster_upper = monster_display.upper().replace(" ", "_")

    # 1. Always update area definitions (hardcoded or parsed)
    template_text = update_template(template_text, monster_upper, locations_text)

    # 2. Now replace all MONSTER references with the proper name
    filled = template_text.replace("VAR_MONSTER_", f"VAR_{monster_upper}_")
    filled = filled.replace("CONST_MONSTER_", f"CONST_{monster_upper}_")
    filled = filled.replace("CONST_AREA_MONSTER", f"CONST_AREA_{monster_upper}")
    
    # Replace group: MONSTER with cleaned monster name
    filled = filled.replace('group: MONSTER', f'group: {monster_display}')

    enum_order = [
        "UNIQUE", "ALWAYS", "SUPPLIES", "WEAPONSANDARMOUR",
        "RUNESANDAMMUNITION", "MATERIALS", "OTHER", "TERTIARY"
    ]

    for enum_key in enum_order:
        placeholder = f"__{enum_key}_ENUM__"
        if enum_key in drop_categories:
            enum_list = format_enum_block(drop_categories[enum_key])
            filled = filled.replace(placeholder, enum_list)
        # else: leave the placeholder so the section can be removed

    # First remove empty sections with markers
    filled = remove_empty_sections(filled, enum_order)
    
    # Then remove any remaining START/END markers with more thorough patterns
    filled = re.sub(r'//\s*START_\w+\s*\n', '', filled)  # More flexible START pattern
    filled = re.sub(r'//\s*END_\w+\s*\n?', '', filled)   # More flexible END pattern
    
    # Clean up any resulting double blank lines
    filled = re.sub(r'\n{3,}', '\n\n', filled)
    
    return filled

def run_batch(monster_list_file='bosses.txt', template_path='boss_template.txt', output_dir='output'):
    groups = parse_monster_list(monster_list_file)

    with open(template_path, 'r', encoding='utf-8') as f:
        template_text = f.read()

    os.makedirs(output_dir, exist_ok=True)
    merged_results = []

    for group_name, monster_list in groups:
        try:
            print(f"\n→ Processing: {group_name} ({', '.join(monster_list)})")
            combined_drops = defaultdict(set)
            combined_locations = []

            for monster in monster_list:
                wikitext = get_wikitext(monster)
                # Extract locations section - check both singular and plural
                locations_section = ""
                if "\n==Locations==" in wikitext:
                    locations_section = wikitext.split("\n==Locations==")[1].split("\n==")[0]
                elif "\n==Location==" in wikitext:
                    locations_section = wikitext.split("\n==Location==")[1].split("\n==")[0]

                if locations_section:
                    combined_locations.append(locations_section)
                
                drops = extract_categorized_drops(wikitext)
                for k, v in drops.items():
                    combined_drops[k].update(v)
            
            # Join all location sections
            all_locations = "\n".join(combined_locations) if combined_locations else None
            
            # Sort and deduplicate drops
            combined_drops = {k: sorted(v) for k, v in combined_drops.items() if v}
            
            filled_text = fill_code_template(
                group_name, 
                combined_drops, 
                template_text,
                all_locations
            )

            output_file = os.path.join(output_dir, f"output_{group_name.replace(' ', '_')}.txt")
            with open(output_file, 'w', encoding='utf-8') as f_out:
                f_out.write(filled_text)
            print(f"✔ Saved individual file: {output_file}")

            merged_results.append(f"// ==== {group_name} Drops ====\n\n{filled_text}\n")

        except Exception as e:
            print(f"✘ Failed to process {group_name}: {e}")

    if merged_results:
        merged_file = os.path.join(output_dir, "merged_output.txt")
        with open(merged_file, 'w', encoding='utf-8') as f_merge:
            # Remove the "==== Monster Drops ====" headers and join
            cleaned_results = [re.sub(r'// ==== .* Drops ====\n\n', '', result) 
                             for result in merged_results]
            f_merge.write("\n".join(cleaned_results))
        print(f"\n✔ Merged output saved to: {merged_file}")

def parse_monster_list(monster_list_file):
    groups = []
    with open(monster_list_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            if '{' in line and '}' in line:
                group_name, rest = line.split('{', 1)
                group_name = group_name.strip()
                monsters = [m.strip() for m in rest.rstrip('}').split(';')]
                groups.append((group_name, monsters))
            else:
                groups.append((line, [line]))
    return groups

def parse_coordinates(loc_text):
    """Parse x,y coordinates from location text."""
    coords = []
    print(f"DEBUG: Parsing coordinates from: {loc_text}")
    
    # Updated patterns to handle all coordinate formats
    patterns = [
        r'\|x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?)',     # |x:1234.5,y:5678.9
        r'x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?)',       # x:1234.5,y:5678.9
        r'\|(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)(?:\||$)', # |1234.5,5678.9|
        r'(?:^|\|)(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)(?:\||$)',  # Direct pairs with decimals
        r'(?:^|\s)(\d+),(\d+)(?:\s|$)'               # Simple space-separated pairs
    ]
    
    # Try each pattern until coordinates are found
    for pattern in patterns:
        matches = list(re.finditer(pattern, loc_text))
        if matches:
            print(f"DEBUG: Found matches with pattern: {pattern}")
            for match in matches:
                try:
                    x = round(float(match.group(1)))
                    y = round(float(match.group(2)))
                    coords.append((x, y))
                    print(f"DEBUG: Added coordinates: ({x}, {y})")
                except (ValueError, TypeError) as e:
                    print(f"DEBUG: Error parsing coordinates: {e}")
            if coords:  # If we found valid coordinates, stop looking
                break
    
    return coords

def extract_location(location_text):
    """Extract clean location name from wiki format."""
    # Remove all reference tags first
    location_text = re.sub(r'<ref[^>]*?/>|<ref[^>]*?>.*?</ref>', '', location_text)
    
    # Clean up location text first
    location_text = (location_text
        .replace('[[[[', '[[')  # Fix quadruple brackets
        .replace(']]]]', ']]')  # Fix quadruple closing brackets
        .replace('[[/', '[[')   # Fix malformed slash brackets
        .replace('//', '/')     # Fix double slashes
        .strip())               # Remove leading/trailing whitespace
    
    # Handle nested brackets
    while '[[' in location_text and ']]' in location_text:
        # Find innermost bracketed content first
        bracket_match = re.search(r'\[\[([^\[\]]*?)\]\]', location_text)
        if not bracket_match:
            break
            
        linked_location = bracket_match.group(1)
        # Handle pipe characters
        if '|' in linked_location:
            linked_location = linked_location.split('|')[0]
        
        # Clean up any parenthetical suffixes
        if '(' in linked_location:
            base_name = linked_location.split('(')[0].strip()
            # Check for special location suffixes
            if any(suffix in linked_location.lower() for suffix in ['(location)', '(dungeon)']):
                linked_location = base_name
            else:
                # Keep other suffixes like (Upper), (Lower), etc.
                suffix_match = re.search(r'\((Upper|Lower|Middle)\s*(?:Level)?\)', linked_location)
                if suffix_match:
                    linked_location = f"{base_name}({suffix_match.group(1)})"
                else:
                    linked_location = base_name
        
        # Replace just this bracketed section
        location_text = location_text.replace(f'[[{bracket_match.group(1)}]]', linked_location)
    
    return location_text.strip()

def group_coordinates_by_proximity(coords, max_distance=32):
    """Group coordinates that are within max_distance of each other."""
    if not coords:
        return []
    
    groups = []
    used = set()
    
    for i, (x1, y1) in enumerate(coords):
        if i in used:
            continue
            
        # Start a new group
        current_group = [(x1, y1)]
        used.add(i)
        
        # Check all other points
        for j, (x2, y2) in enumerate(coords):
            if j in used:
                continue
            
            # Check if any point in current_group is close to this point
            for gx, gy in current_group:
                distance = max(abs(gx - x2), abs(gy - y2))
                if distance <= max_distance:
                    current_group.append((x2, y2))
                    used.add(j)
                    break
        
        groups.append(current_group)
    
    return groups

def clean_single_location(text):
    """Clean a single location name without slash separators."""
    # Remove reference tags
    text = re.sub(r'<ref[^>]*?/>|<ref[^>]*?>.*?</ref>', '', text)
    
    # Handle wiki brackets
    while '[[' in text and ']]' in text:
        match = re.search(r'\[\[([^\[\]]*?)\]\]', text)
        if not match:
            break
        
        content = match.group(1)
        # Handle piped links
        if '|' in content:
            content = content.split('|')[0]
        
        # Clean up suffixes - remove requirement text in parentheses
        if '(' in content:
            base_name = content.split('(')[0].strip()
            # Check for special location suffixes vs requirements
            if re.search(r'\((Upper|Lower|Middle)\s*(?:Level)?\)', content, re.IGNORECASE):
                suffix = re.search(r'\((Upper|Lower|Middle)\s*(?:Level)?\)', content).group(1)
                content = f"{base_name}({suffix})"
            elif re.search(r'\((.*?(?:required|requires|task|only|slayer).*?)\)', content, re.IGNORECASE):
                # This is a requirement suffix - remove it
                content = base_name
            else:
                content = base_name
        
        text = text.replace(f'[[{match.group(1)}]]', content)
    
    return text.strip()

def clean_location_name(location_name):
    """Clean up location name and remove special suffixes."""
    # Fix malformed brackets
    location_name = re.sub(r'\[{2,}', '[[', location_name)
    location_name = re.sub(r'\]{2,}', ']]', location_name)
    location_name = location_name.replace('_', ' ')
    
    # Handle locations with slashes (nested locations)
    if '/' in location_name:
        parts = location_name.split('/')
        cleaned_parts = [clean_single_location(part.strip()) for part in parts]
        return '/'.join(cleaned_parts)
    
    # Regular single location cleanup
    return clean_single_location(location_name)

def format_area_constants(monster_name, locations_text, buffer_size=10):
    """Generate area constants for a monster's locations with buffer zone."""
    area_blocks = []
    current_area = 0
    location_groups = []  # Initialize location_groups list here
    
    # Check for hardcoded locations first
    normalized_name = monster_name.upper().replace(" ", "_").replace("'", "")
    if normalized_name in HARDCODED_LOCATIONS:
        print(f"DEBUG: Using hardcoded location for {normalized_name}")
        hardcoded = HARDCODED_LOCATIONS[normalized_name]
        for min_x, min_y, min_z, max_x, max_y, max_z in hardcoded["coords"]:
            area_constant = (
                f"#define CONST_AREA_{monster_name}{current_area} "
                f"[{min_x},{min_y},{min_z},{max_x},{max_y},{max_z}] // [[{hardcoded['name']}]]\n"
            )
            area_blocks.append(area_constant)
            current_area += 1
        
        # Generate rule for hardcoded locations
        if area_blocks:
            area_refs = " || ".join(f"area:CONST_AREA_{monster_name}{i}" 
                                  for i in range(current_area))
            rule_def = f"#define CONST_{monster_name}_RULE(_cond) rule (({area_refs}) && (_cond))"
            area_blocks.append(rule_def)
            return "".join(area_blocks)
    
    # Split into location blocks
    loc_blocks = re.findall(r'\{\{LocLine(.*?)\}\}', locations_text, re.DOTALL)
    
    # First collect coordinates grouped by location
    for block in loc_blocks:
        coords = parse_coordinates(block)
        if coords:
            location_match = re.search(r'\|location = ([^\n|]*)', block)
            if location_match:
                location_text = location_match.group(1).strip()
                location_name = clean_location_name(location_text)
                location_groups.append((location_name.strip(), coords))
    
    # Process each location separately
    for location_name, coords in location_groups:
        coord_groups = group_coordinates_by_proximity(coords)
        
        for group in coord_groups:
            if group:
                min_x = min(x for x, _ in group)
                min_y = min(y for _, y in group)
                max_x = max(x for x, _ in group)
                max_y = max(y for _, y in group)
                
                # Add buffer zone
                min_x = max(0, min_x - buffer_size)
                min_y = max(0, min_y - buffer_size)
                max_x = max_x + buffer_size
                max_y = max_y + buffer_size
                
                # Add newline to area constant definition
                area_constant = (
                    f"#define CONST_AREA_{monster_name}{current_area} "
                    f"[{min_x},{min_y},0,{max_x},{max_y},0] // [[{location_name}]]\n"
                )
                area_blocks.append(area_constant)
                current_area += 1
    
    # Generate single rule combining all areas
    if area_blocks:
        area_refs = " || ".join(f"area:CONST_AREA_{monster_name}{i}" 
                              for i in range(current_area))
        rule_def = f"#define CONST_{monster_name}_RULE(_cond) rule (({area_refs}) && (_cond))"
        area_blocks.append(rule_def)
    
    return "".join(area_blocks)  # Join without additional newlines

def update_template(template_text, monster_name, locations_text):
    """Replace placeholder area definitions with actual coordinates."""
    normalized_name = monster_name.upper().replace(" ", "_").replace("'", "")

    # Pattern matches any boss's area section (MONSTER or already replaced)
    area_pattern = (
        r'#define CONST_AREA_[A-Z0-9_]+0[^\n]*\n'
        r'#define CONST_[A-Z0-9_]+_RULE\(_cond\)[^\n]*\n'
    )

    if normalized_name in HARDCODED_LOCATIONS:
        print(f"DEBUG: Using hardcoded template for {normalized_name}")
        new_section = HARDCODED_LOCATIONS[normalized_name]["template"] + "\n"
        template_text = re.sub(area_pattern, new_section, template_text, flags=re.DOTALL)
    else:
        area_constants = format_area_constants(monster_name, locations_text)
        if area_constants:
            print(f"DEBUG: Using parsed locations for {normalized_name}")
            template_text = re.sub(area_pattern, area_constants + "\n", template_text, flags=re.DOTALL)
            match = re.search(area_pattern, template_text, flags=re.DOTALL)
            if match:
                print("DEBUG: Matched area section:\n", match.group(0))
            else:
                print("DEBUG: No match found for area section!")

    return template_text

if __name__ == "__main__":
    run_batch()
