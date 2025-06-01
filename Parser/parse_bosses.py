import requests
import mwparserfromhell
from collections import defaultdict
import os
import re

# Settings Toggles
print_single_monster_outputs = False  # Set to True to write individual files
output_merged_file = True  # Set to False to skip writing Monsters_Wiki_Parse.txt
show_progress = True  # Set to False to suppress progress output
stop_on_error = True  # Set to True to halt on first error
overwrite_outputs = True  # Set to False to skip writing if file already exists
output_dir = "output"  # Change this to set a different output folder

# Distance Toggles
adjacent_group_range = 32  # Default: 32 - Max distance for grouping adjacent coordinates
wander_range_distance = 10  # Default: 10 - Buffer to add around coordinates for area definitions to account for wander range

# Debug Toggles
limit_monsters = None  # Set to an integer to limit, or None for all to limit the number of monsters processed for testing
debug_monsters = False  # Set to True to print each monster before processing
debug_drops = False  # Set to True to print debug info about drops
debug_locations = False  # Set to True to print debug info about locations
debug_enum_mapping = False  # Set to True to print debug info about section-to-enum mapping
print_unmapped_sections = False  # Set to True to print all unique unmapped section headings at the end


unmapped_sections = set()

# Map section title aliases (all lowercase) to enum Categories
# You can add or remove categories as desired
# If you add, remove, or change the order of the categories, you must update the enum_order in fill_code_template
SECTION_ALIASES = {
    "ALWAYS": ["100%", "frozen tears", "ancient shards"],
    "SUPPLIES": ["supplies", "potions", "consumables", "secondary supply roll", "minor drops"],
    "WEAPONSANDARMOUR": ["weapons and armour", "weapons", "armour", "staves", "battleaxes"],
    "RUNESANDAMMUNITION": ["runes and ammunition", "runes", "ammunition", "elemental runes", "catalytic runes", "combination runes"],
    "MATERIALS": ["materials", "herbs", "seeds", "ores and bars", "fish", "fishing", "bait", "bolt tips", "resources", "noted herbs", "food", "talismans", "talismans (noted)", "gemstones", "dragonhide", "fletching materials", "tree-herb seed drop table"],
    "OTHER": ["other", "gloves", "jewellery", "junk", "catacombs drops", "fossils"],
    "TERTIARY": ["tertiary", "ancient statuettes", "secondary", "catacombs tertiary", "chasm of fire tertiary", "wilderness slayer tertiary"],
    "UNIQUE": ["unique", "uniques", "pre-roll", "sigils", "mutagens", "secondary uniques"]
}

# Items that should be ignored in drop table data from the wiki
IGNORE_ITEMS = {"Nothing", "Coins"}

# Some drop tables on the wiki are merely references to templates that contain the actual items.
# This dictionary maps those templates to the items they contain.
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

# Hardcoded location for the Bosses whose spawn locations are missing from the wiki
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

def extract_template_params(template):
    """
    Return a dictionary of all parameters in a mwparserfromhell Template node.
    Strips code and whitespace from each value.
    """
    params = {}
    for param in template.params:
        key = str(param.name).strip().lower()
        value = param.value.strip_code().strip()
        params[key] = value
    return params

def extract_section(wikitext, section_names):
    """
    Extract the content of the first section whose heading matches one of section_names (case-insensitive).
    Returns the section content as a string, or "" if not found.
    """
    code = mwparserfromhell.parse(wikitext)
    section_names = {name.lower().strip() for name in section_names}
    found = False
    extracted = []
    for node in code.nodes:
        if isinstance(node, mwparserfromhell.nodes.Heading) and node.level == 2:
            heading_title = node.title.strip().lower()
            if found:
                # End of the section
                break
            if heading_title in section_names:
                found = True
                continue  # Don't include the heading itself
        if found:
            extracted.append(str(node))
    return "".join(extracted).strip()

def extract_all_drop_sections(wikitext):
    """
    Extract and combine all drop-related sections (e.g., Drops, Wilderness Slayer Cave drops).
    Returns a single wikitext string containing all drop sections.
    """
    code = mwparserfromhell.parse(wikitext)
    drop_section_titles = []
    # Collect all level 2 headings containing 'drops'
    for node in code.nodes:
        if isinstance(node, mwparserfromhell.nodes.Heading) and node.level == 2:
            title = node.title.strip().lower()
            if "drops" in title:
                drop_section_titles.append(title)
    # Extract all such sections and concatenate
    all_drops = []
    for section_title in drop_section_titles:
        section = extract_section(wikitext, {section_title})
        if section:
            all_drops.append(section)
    return "\n".join(all_drops)

def strip_wiki_markup(text):
    """
    Remove wiki markup (links, tags, templates, references) and return plain text.
    """
    # Remove <ref>...</ref> and <ref .../> tags before parsing
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<ref[^>]*/>', '', text, flags=re.DOTALL | re.IGNORECASE)
    code = mwparserfromhell.parse(text)
    cleaned = []
    for node in code.nodes:
        # Remove references, comments, and tags
        if isinstance(node, (mwparserfromhell.nodes.Tag, mwparserfromhell.nodes.Comment)):
            continue
        # Replace wikilinks with their display text or title
        if isinstance(node, mwparserfromhell.nodes.Wikilink):
            if node.text:
                cleaned.append(str(node.text))
            else:
                cleaned.append(str(node.title))
            continue
        # Replace templates with their display text if possible, else skip
        if isinstance(node, mwparserfromhell.nodes.Template):
            # For simple templates, try to use the first parameter as display
            if node.params:
                cleaned.append(node.params[0].value.strip_code().strip())
            continue
        # Otherwise, just add the plain text
        cleaned.append(str(node))
    result = "".join(cleaned).strip()
    # Now remove any leftover brackets or whitespace
    result = result.replace('[[', '').replace(']]', '').strip()
    # Remove any double spaces left by tag removal
    result = re.sub(r'\s{2,}', ' ', result)
    return result

def map_section_to_enum(section_title):
    section_title_clean = section_title.lower().strip()
    for enum_key, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            if alias in section_title_clean:
                if debug_enum_mapping:
                    print(f"DEBUG: Section heading '{section_title}' mapped to enum '{enum_key}' (via alias '{alias}')")
                return enum_key
    if debug_enum_mapping:
        print(f"DEBUG: Section heading '{section_title}' mapped to enum 'None'")
    unmapped_sections.add(section_title.strip())
    return None

# Accessing the Old School RuneScape Wiki API to get wikitext JSON for a given page title
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

# Extract items from nodes in the wikitext
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

# Extract categorized drops from the wikitext
def extract_categorized_drops(wikitext):
    """
    Extract categorized drops from the wikitext using mwparserfromhell.
    Handles subsections and adjacent templates robustly.
    """
    code = mwparserfromhell.parse(wikitext)
    categorized_drops = defaultdict(set)

    # Walk each section (including subsections)
    for section in code.get_sections(include_headings=True, flat=True):
        headings = section.filter_headings()
        if not headings:
            continue
        heading_title = headings[0].title.strip()
        section_key = map_section_to_enum(heading_title)
        if not section_key:
            continue

        # Find all drop templates in this section
        for template in section.ifilter_templates(recursive=True):
            template_name = str(template.name).strip()
            if template_name in {"DropsLine", "Drops line"}:
                item = None
                for param in ['item', 'name', 'drop']:
                    if template.has(param):
                        item = template.get(param).value.strip_code().strip()
                        break
                if item and item not in IGNORE_ITEMS:
                    item = strip_wiki_markup(item)
                    categorized_drops[section_key].add(item)
            elif template_name in DROP_TABLE_TEMPLATES:
                categorized_drops[section_key].update(DROP_TABLE_TEMPLATES[template_name])

    # Remove empty categories and sort
    categorized_drops = {k: sorted(v) for k, v in categorized_drops.items() if v}

    return categorized_drops

def format_enum_block(items):
    if not items:
        return "[]"
    return "[" + ", ".join(f'"{item}"' for item in items) + "]"

# Remove empty sections based on blank enum keys
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
    
    # Update area definitions if locations are provided
    if locations_text:
        template_text = update_template(template_text, monster_upper, locations_text)
    
    # Replace all MONSTER references with the proper name
    filled = template_text.replace("VAR_MONSTER_", f"VAR_{monster_upper}_")
    filled = filled.replace("CONST_MONSTER_", f"CONST_{monster_upper}_")
    filled = filled.replace("CONST_AREA_MONSTER", f"CONST_AREA_{monster_upper}")
    
    # Replace group: MONSTER with cleaned monster name
    filled = filled.replace('group: MONSTER', f'group: {monster_display}')

# You must update the enum order to match your template sections if you make changes
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

# Settings for running the batch processing
def run_batch(monster_list_file='bosses.txt', template_path='boss_template.txt', output_dir='output'):
    groups = parse_monster_list(monster_list_file)

    with open(template_path, 'r', encoding='utf-8') as f:
        template_text = f.read()

    os.makedirs(output_dir, exist_ok=True)
    merged_results = []

    for i, (group_name, monster_list) in enumerate(groups):
        if limit_monsters is not None and i >= limit_monsters:
            break
        if show_progress:
            print(f"Processing group: {group_name} ({len(monster_list)} monsters)")
        try:
            combined_drops = defaultdict(set)
            combined_locations = []

            for monster in monster_list:
                if debug_monsters:
                    print(f"Processing monster: '{monster}'")
                wikitext = get_wikitext(monster)
                # Extract locations section - check both singular and plural
                locations_section = extract_section(wikitext, {"locations", "location"})

                if locations_section:
                    if debug_locations:
                        print(f"DEBUG: {monster} locations section:\n{locations_section}")
                    combined_locations.append(locations_section)
                
                drops_section = extract_section(wikitext, {"drops"})
                if debug_drops:
                    print(f"DEBUG: Extracted drops section for {monster}:\n{drops_section[:500]}")
                all_drops_section = extract_all_drop_sections(wikitext)
                drops = extract_categorized_drops(all_drops_section if all_drops_section else wikitext)
                if debug_drops:
                    print(f"DEBUG: {monster} categorized drops: {dict(drops)}")
                for k, v in drops.items():
                    combined_drops[k].update(v)
            
            # Join all location sections
            all_locations = "\n".join(combined_locations) if combined_locations else None

            if debug_locations:
                print(f"DEBUG: Combined locations for {group_name}:\n{all_locations}")
            
            # Sort and deduplicate drops
            combined_drops = {k: sorted(v) for k, v in combined_drops.items() if v}

            if debug_drops:
                print(f"DEBUG: Combined drops for {group_name}: {dict(combined_drops)}")
            
            # Use group_name for output, but only use combined drops/locations from members
            filled_text = fill_code_template(
                group_name, 
                combined_drops, 
                template_text,
                all_locations
            )

            # Only write individual output files if enabled
            if print_single_monster_outputs:
                output_file = os.path.join(output_dir, f"output_{group_name.replace(' ', '_')}.txt")
                if overwrite_outputs or not os.path.exists(output_file):
                    with open(output_file, 'w', encoding='utf-8') as f_out:
                        f_out.write(filled_text)

            merged_results.append(f"// ==== {group_name} Drops ====\n\n{filled_text}\n")

        except Exception as e:
            print(f"✘ Failed to process {group_name}: {e}")
            if stop_on_error:
                raise

    if merged_results and output_merged_file:
        merged_file = "Bosses_Wiki_Parse.txt" # Name of the merged output file
        if overwrite_outputs or not os.path.exists(merged_file):
            with open(merged_file, 'w', encoding='utf-8') as f_merge:
                # Remove the "==== Monster Drops ====" headers and join
                cleaned_results = [re.sub(r'// ==== .* Drops ====\n\n', '', result) 
                                 for result in merged_results]
                f_merge.write("\n".join(cleaned_results))
        else:
            print(f"Skipped writing {merged_file} (overwrite_outputs=False and file exists)")

    if print_unmapped_sections and unmapped_sections:
        print("\nUnmapped section headings (unique):")
        for heading in sorted(unmapped_sections):
            print(f"  - {heading}")

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

# Parse x,y coordinates from location text on the wiki.
def parse_coordinates(loc_text):
    """Parse x,y coordinates from location text."""
    coords = []
    
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
            for match in matches:
                try:
                    x = round(float(match.group(1)))
                    y = round(float(match.group(2)))
                    coords.append((x, y))
                except (ValueError, TypeError):
                    pass
            if coords:
                break
    return coords

def extract_location(location_text):
    """Extract clean location name from wiki format."""
    # Use mwparserfromhell-based cleaner for robust markup removal
    return strip_wiki_markup(location_text).strip()

def group_coordinates_by_proximity(coords, max_distance=adjacent_group_range):
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
    # Remove <ref>...</ref> and <ref .../> tags before further processing
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<ref[^>]*/>', '', text, flags=re.DOTALL | re.IGNORECASE)
    return strip_wiki_markup(text)

def clean_location_name(location_name):
    """Clean up location name and remove special suffixes."""
    # Remove <ref>...</ref> and <ref .../> tags FIRST
    location_name = re.sub(r'<ref[^>]*>.*?</ref>', '', location_name, flags=re.DOTALL | re.IGNORECASE)
    location_name = re.sub(r'<ref[^>]*/>', '', location_name, flags=re.DOTALL | re.IGNORECASE)
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

def format_area_constants(monster_name, locations_text, buffer_size=wander_range_distance):
    """Generate area constants for a monster's locations with buffer zone."""
    area_blocks = []
    current_area = 0
    location_groups = []  # Initialize location_groups list here
    
    # Check for hardcoded locations first
    normalized_name = monster_name.upper().replace(" ", "_").replace("'", "")
    if normalized_name in HARDCODED_LOCATIONS:
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

    # Parse the locations_text as wikitext using mwparserfromhell
    code = mwparserfromhell.parse(locations_text)
    for template in code.filter_templates():
        if template.name.matches("LocLine"):
            # Extract coordinates
            block = str(template)
            coords = parse_coordinates(block)
            if coords:
                # Extract location name
                location_text = ""
                if template.has("location"):
                    location_text = str(template.get("location").value).strip()
                else:
                    # Fallback: try to extract from raw block
                    location_match = re.search(r'\|location\s*=\s*([^\n|}]*)', block)
                    if location_match:
                        location_text = location_match.group(1).strip()
                if location_text:
                    location_name = clean_location_name(location_text)
                    location_groups.append((location_name, coords))

    # Process each location separately
    for location_name, coords in location_groups:
        # Group coordinates within this location
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
                
                # Re-wrap location name in double brackets for output
                area_constant = (
                    f"#define CONST_AREA_{monster_name}{current_area} "
                    f"[{min_x},{min_y},0,{max_x},{max_y},0] // [[{location_name}]]"
                )
                area_blocks.append(area_constant)
                current_area += 1
    
    # Generate the rule combining all areas
    if area_blocks:
        area_refs = " || ".join(f"area:CONST_AREA_{monster_name}{i}" 
                              for i in range(len(area_blocks)))
        rule_def = (
            f"#define CONST_{monster_name}_RULE(_cond) "
            f"rule (({area_refs}) && (_cond))"
        )
        area_blocks.append(rule_def)
    
    return "\n".join(area_blocks)

def update_template(template_text, monster_name, locations_text):
    """Replace placeholder area definitions with actual coordinates."""
    area_constants = format_area_constants(monster_name, locations_text)
    
    # Replace the placeholder area definitions
    pattern = r'#define CONST_AREA_MONSTER.*?(?=\n\n|$)'
    template_text = re.sub(pattern, area_constants, template_text, flags=re.DOTALL)
    
    return template_text

if __name__ == "__main__":
    run_batch()
