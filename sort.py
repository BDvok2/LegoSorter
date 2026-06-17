import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")

SORT_SYSTEM_PROMPT = """
You are a LEGO part sorting assistant.

Input:
- LEGO part name
- LEGO part ID

The part name is the primary source of truth. The ID is only a secondary hint if the name is unclear.

Analyze the keywords in the part name and choose exactly ONE storage location from the list below.

BOX 1
Small 1:
- Technic pins
Small 2:
- Technic axles
Small 3:
- Technic gears
Small 4:
- Other Technic connectors (bushings, joints, small beams)
Big:
- Technic beams, frames, large connectors

BOX 2
Small 1:
- 1×1 plates, bricks, and round pieces
Small 2:
- 1×2 plates and bricks
Small 3:
- Small tiles
Small 4:
- Modified parts (clips, brackets, jumpers, SNOT parts, hinges, bars)
Big:
- Regular bricks (2×2, 2×3, 2×4, similar) and standard plates

BOX 3
Small 1:
- Minifigure heads
Small 2:
- Minifigure hair, helmets, hats
Small 3:
- Minifigure accessories, tools, weapons, backpacks
Small 4:
- Minifigure legs and torsos
Big:
- Wheels, tires, vehicle parts, large panels, walls

BOX 4
Small 1:
- Transparent pieces
Small 2:
- Plants, animals, food
Small 3:
- Strings, chains, rubber
Small 4:
- Small slopes, curved pieces, printed pieces
Big:
- Doors, windows, arches, large slopes, medium special parts

Keyword rules:
- "Technic Pin" → Box 1 Small 1: Technic pins
- "Technic Axle" → Box 1 Small 2: Technic axles
- "Gear" → Box 1 Small 3: Technic gears
- "Plate 1 x 1" → Box 2 Small 1: 1×1 plates, bricks, and round pieces
- "Plate 1 x 2" → Box 2 Small 2: 1×2 plates and bricks
- "Brick 1 x 1" → Box 2 Small 1: 1×1 plates, bricks, and round pieces
- "Brick 1 x 2" → Box 2 Small 2: 1×2 plates and bricks
- "Tile" → Box 2 Small 3: Small tiles
- "Slope" → Box 4 Small 4 if small, Box 4 Big if large
- "Minifigure" or "Minifig" → Box 3 appropriate category
- "Wheel" or "Tire" → Box 3 Big: Wheels, tires, vehicle parts
- "Window", "Door", "Arch" → Box 4 Big: Doors, windows, arches
- "Transparent", "Trans", "Clear" → Box 4 Small 1: Transparent pieces
- "Plant", "Leaf", "Animal", "Food" → Box 4 Small 2: Plants, animals, food

Important:
- Use the most specific match.
- The exact words in the part name have priority over assumptions.
- Do NOT explain.
- Reply with ONLY the exact location.

Examples:
Box 1 — Small 1: Technic pins
Box 2 — Big: Regular bricks and standard plates
Box 3 — Small 1: Minifigure heads
Box 4 — Big: Doors, windows, arches
Box 2 — Small 4: Modified parts
"""

CAVITY_MAP = {
    "1": {
        "technic pins": 1,
        "technic axles": 2,
        "technic gears": 3,
        "other technic connectors": 4,
        "technic beams, frames, and large connectors": 5,
        "plates (all sizes)": 6,
        "plates": 6,
    },
    "2": {
        "1\u00d71 pieces (bricks, plates, round pieces)": 1,
        "1\u00d71 pieces": 1,
        "1\u00d72 pieces": 2,
        "small tiles": 3,
        "modified parts (clips, brackets, jumpers, snot pieces)": 4,
        "modified parts": 4,
        "regular bricks (2\u00d72, 2\u00d73, 2\u00d74, and similar)": 5,
        "regular bricks": 5,
        "slopes and curved pieces": 6,
        "slopes and curved": 6,
    },
    "3": {
        "minifigure heads": 1,
        "minifigure hair, helmets, and hats": 2,
        "minifigure hair": 2,
        "minifigure accessories (tools, weapons, backpacks, etc.)": 3,
        "minifigure accessories": 3,
        "minifigure legs and torsos": 4,
        "minifigure legs": 4,
        "wheels, tires, and vehicle parts": 5,
        "wheels and tires": 5,
        "large special pieces (panels, walls, large decorative parts, large vehicle pieces)": 6,
        "large special pieces": 6,
    },
    "4": {
        "transparent small pieces": 1,
        "printed pieces": 2,
        "plants, animals, and food pieces": 3,
        "plants and animals": 3,
        "strings, chains, and rubber pieces": 4,
        "strings and chains": 4,
        "doors, windows, arches, and medium special parts": 5,
        "doors and windows": 5,
        "standard bricks and bulk bricks (2\u00d72, 2\u00d73, 2\u00d74, larger bricks)": 6,
        "standard bricks": 6,
    },
    "5": {
        "1\u00d71 plates": 1,
        "1\u00d71 bricks": 2,
        "1\u00d71 round pieces": 3,
        "1\u00d72 plates": 4,
        "1\u00d72 bricks": 5,
        "jumper plates": 6,
        "clips": 7,
        "bars": 8,
        "brackets": 9,
        "hinges": 10,
        "snot bricks": 11,
        "small slopes": 12,
        "small curved pieces": 13,
        "tiny transparent pieces": 14,
        "small printed pieces": 15,
        "stud shooters and tiny special elements": 16,
        "stud shooters": 16,
        "empty/overflow": 17,
        "empty": 17,
    },
}


def normalize_compartment(text):
    s = text.lower()
    s = re.sub(r"\s*(small|big|giant|enormous|detail)\s*:\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def lookup_cavity(box, compartment):
    raw = normalize_compartment(compartment)
    box_map = CAVITY_MAP.get(box, {})
    exact = box_map.get(raw)
    if exact:
        return exact
    for key, idx in box_map.items():
        if raw in key or key in raw:
            return idx
    return None


def classify_part(part_name, part_id):
    if not GROQ_API_KEY:
        return "Box 5 — Detail: Empty/overflow"

    client = Groq(api_key=GROQ_API_KEY)

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SORT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Part name: {part_name}, Part ID: {part_id}"},
            ],
            temperature=0.6,
            reasoning_effort="default",
            max_completion_tokens=4096,
            top_p=0.95,
        )
        text = response.choices[0].message.content or ""
        matches = list(re.finditer(r"Box\s+\d+\s*[—\-–]\s*(?:Small|Big|Giant|Enormous|Detail)\s*:?\s*[^.\n]+", text))
        if matches:
            return matches[-1].group(0).strip()
        return "Box 5 — Detail: Empty/overflow"
    except Exception as e:
        return f"Box 5 — Detail: Empty/overflow (error: {e})"


def parse_sort_result(result):
    m = re.match(r"Box\s+(\d+)\s*[—\-–]\s*(.*)", result)
    if m:
        return m.group(1), m.group(2).strip()
    return None, result


_CACHE: dict = {}

def classify(part_name, part_id):
    if part_id in _CACHE:
        return _CACHE[part_id]
    result = classify_part(part_name, part_id)
    box, compartment = parse_sort_result(result)
    cavity = lookup_cavity(box, compartment)
    cached = (result, box, compartment, cavity)
    _CACHE[part_id] = cached
    return cached
