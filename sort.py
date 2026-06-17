import json
import re

STORAGE_LOCATIONS = {
    "1": {
        "Small 1": "Technic pins",
        "Small 2": "Technic axles",
        "Small 3": "Technic gears",
        "Small 4": "Technic connectors (bushings, joints, small beams)",
        "Big": "Technic beams, frames, large connectors",
    },
    "2": {
        "Small 1": "1\u00d71 plates, bricks, and round pieces",
        "Small 2": "1\u00d72 plates and bricks",
        "Small 3": "Small tiles",
        "Small 4": "Modified parts (clips, brackets, jumpers, SNOT, hinges, bars)",
        "Big": "Regular bricks (2\u00d72, 2\u00d74, etc.) and Standard Plates",
    },
    "3": {
        "Small 1": "Minifigure heads",
        "Small 2": "Minifigure hair, helmets, hats",
        "Small 3": "Minifigure accessories, tools, weapons, backpacks",
        "Small 4": "Minifigure legs and torsos",
        "Big": "Wheels, tires, vehicle parts, doors, windows, arches",
    },
    "4": {
        "Small 1": "Transparent pieces, printed pieces, stud shooters",
        "Small 2": "Plants, animals, food",
        "Small 3": "Strings, chains, rubber",
        "Small 4": "Small slopes and curved pieces",
        "Big": "Large slopes, panels, walls, enormous bulk bricks",
    },
}

CAVITY_NUMBER = {
    "Small 1": 1,
    "Small 2": 2,
    "Small 3": 3,
    "Small 4": 4,
    "Big": 5,
}

RULES = [
    (r"(?i)\btechnic\s*pin", "1", "Small 1"),
    (r"(?i)\btechnic\s*axle", "1", "Small 2"),
    (r"(?i)\btechnic\s*gear", "1", "Small 3"),
    (r"(?i)\b(?:technic\s+)?(?:bushing|joint|connector)\b.*\btechnic", "1", "Small 4"),
    (r"(?i)\btechnic\s*(?:connector|bushing|joint)", "1", "Small 4"),
    (r"(?i)\btechnic\s*(?:beam|liftarm|lift.?arm|frame)", "1", "Big"),
    (r"(?i)\btechnic\b", "1", "Big"),

    (r"(?i)\btransparent\b", "4", "Small 1"),
    (r"(?i)\btrans[-\s]", "4", "Small 1"),
    (r"(?i)\bclear\b", "4", "Small 1"),
    (r"(?i)\bprinted\b", "4", "Small 1"),
    (r"(?i)\bstud[-\s]?shooter\b", "4", "Small 1"),

    (r"(?i)\bplate\s+1\s*[x×]\s*1\b", "2", "Small 1"),
    (r"(?i)\bbrick\s+1\s*[x×]\s*1\b", "2", "Small 1"),
    (r"(?i)\bround\s+1\s*[x×]\s*1\b", "2", "Small 1"),
    (r"(?i)\b1\s*[x×]\s*1\b.*\bplate\b", "2", "Small 1"),
    (r"(?i)\b1\s*[x×]\s*1\b.*\bbrick\b", "2", "Small 1"),
    (r"(?i)\bplate\s+1\s*[x×]\s*2\b", "2", "Small 2"),
    (r"(?i)\bbrick\s+1\s*[x×]\s*2\b", "2", "Small 2"),
    (r"(?i)\b1\s*[x×]\s*2\b.*\bplate\b", "2", "Small 2"),
    (r"(?i)\b1\s*[x×]\s*2\b.*\bbrick\b", "2", "Small 2"),
    (r"(?i)\btile\b", "2", "Small 3"),
    (r"(?i)\b(?:clip|bracket|jumper|snot|hinge|bar|modified|headlight)\b", "2", "Small 4"),
    (r"(?i)\bbrick\s+2\s*[x×]", "2", "Big"),
    (r"(?i)\bplate\s+2\s*[x×]", "2", "Big"),
    (r"(?i)\bbrick\s+\d\s*[x×]\s*\d", "2", "Big"),
    (r"(?i)\bbrick\b", "2", "Big"),
    (r"(?i)\bplate\b", "2", "Big"),

    (r"(?i)\bminif(?:ig|igure)\b.*\bhead\b", "3", "Small 1"),
    (r"(?i)\bhead\b.*\bminif(?:ig|igure)\b", "3", "Small 1"),
    (r"(?i)\bminif(?:ig|igure)\b.*\b(?:hair|helmet|hat|crown|cap)\b", "3", "Small 2"),
    (r"(?i)\b(?:hair|helmet|hat|crown|cap)\b.*\bminif(?:ig|igure)\b", "3", "Small 2"),
    (r"(?i)\bminif(?:ig|igure)\b.*\b(?:accessor|tool|weapon|backpack|sword|gun|shield|staff|wand)\b", "3", "Small 3"),
    (r"(?i)\b(?:accessor|tool|weapon|backpack|sword|gun|shield|staff|wand)\b.*\bminif(?:ig|igure)\b", "3", "Small 3"),
    (r"(?i)\bminif(?:ig|igure)\b.*\b(?:leg|torso)\b", "3", "Small 4"),
    (r"(?i)\b(?:leg|torso)\b.*\bminif(?:ig|igure)\b", "3", "Small 4"),
    (r"(?i)\bminif(?:ig|igure)\b", "3", "Small 4"),
    (r"(?i)\bwheel\b", "3", "Big"),
    (r"(?i)\btire\b", "3", "Big"),
    (r"(?i)\btyre\b", "3", "Big"),
    (r"(?i)\bdoor\b", "3", "Big"),
    (r"(?i)\bwindow\b", "3", "Big"),
    (r"(?i)\barch\b", "3", "Big"),
    (r"(?i)\bvehicle\b", "3", "Big"),
    (r"(?i)\bwindshield\b", "3", "Big"),

    (r"(?i)\bplant\b", "4", "Small 2"),
    (r"(?i)\bleaf\b", "4", "Small 2"),
    (r"(?i)\banimal\b", "4", "Small 2"),
    (r"(?i)\bfood\b", "4", "Small 2"),
    (r"(?i)\btree\b", "4", "Small 2"),
    (r"(?i)\bflower\b", "4", "Small 2"),
    (r"(?i)\bstring\b", "4", "Small 3"),
    (r"(?i)\bchain\b", "4", "Small 3"),
    (r"(?i)\brubber\b", "4", "Small 3"),
    (r"(?i)\b(?:small\s+)?slope\s+(?:1|2|3)\s*[x×]\s*(?:1|2)\b", "4", "Small 4"),
    (r"(?i)\bslope\b.*\bcurved\b", "4", "Small 4"),
    (r"(?i)\bcurved\b.*\bslope\b", "4", "Small 4"),
    (r"(?i)\bslope\b", "4", "Big"),
    (r"(?i)\bpanel\b", "4", "Big"),
    (r"(?i)\bwall\b", "4", "Big"),
]


def classify_part(part_name, part_id):
    for pattern, box, cavity in RULES:
        if re.search(pattern, part_name):
            category = STORAGE_LOCATIONS[box][cavity]
            result = {
                "Box": box,
                "Cavity": cavity,
                "Category_Match": category,
            }
            return json.dumps(result)
    return json.dumps({"Box": "2", "Cavity": "Big", "Category_Match": "Regular bricks (2\u00d72, 2\u00d74, etc.) and Standard Plates"})


def parse_sort_result(result):
    data = json.loads(result)
    box = data["Box"]
    cavity_name = data["Cavity"]
    category = data["Category_Match"]
    return box, cavity_name, category


def lookup_cavity(cavity_name):
    return CAVITY_NUMBER.get(cavity_name, 5)


_CACHE: dict = {}


def classify(part_name, part_id):
    cache_key = f"{part_id}:{part_name}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    result = classify_part(part_name, part_id)
    box, cavity_name, category = parse_sort_result(result)
    cavity_num = lookup_cavity(cavity_name)
    result_text = f"Box {box} \u2014 {cavity_name}: {category}"
    cached = (result_text, box, category, cavity_num)
    _CACHE[cache_key] = cached
    return cached
