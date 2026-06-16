import os
import re
from openai import OpenAI

import config

SORT_SYSTEM_PROMPT = """You are a LEGO sorting assistant. Given a LEGO part name and ID, tell me which box and compartment it goes into.

Box 1 (4 small + 1 big + 1 giant):
  Small: Technic pins
  Small: Technic axles
  Small: Technic gears
  Small: Other Technic connectors (bushings, joints, small beams)
  Big: Technic beams, frames, and large connectors
  Giant: Plates (all sizes)

Box 2 (4 small + 1 big + 1 giant):
  Small: 1×1 pieces (bricks, plates, round pieces)
  Small: 1×2 pieces
  Small: Small tiles
  Small: Modified parts (clips, brackets, jumpers, SNOT pieces)
  Big: Regular bricks (2×2, 2×3, 2×4, and similar)
  Giant: Slopes and curved pieces

Box 3 (4 small + 1 big + 1 giant):
  Small: Minifigure heads
  Small: Minifigure hair, helmets, and hats
  Small: Minifigure accessories (tools, weapons, backpacks, etc.)
  Small: Minifigure legs and torsos
  Big: Wheels, tires, and vehicle parts
  Giant: Large special pieces (panels, walls, large decorative parts, large vehicle pieces)

Box 4 (4 small + 1 big + 1 enormous):
  Small: Transparent small pieces
  Small: Printed pieces
  Small: Plants, animals, and food pieces
  Small: Strings, chains, and rubber pieces
  Big: Doors, windows, arches, and medium special parts
  Enormous: Standard bricks and bulk bricks (2×2, 2×3, 2×4, larger bricks)

Box 5 (17 small compartments) — detail box:
  1×1 plates | 1×1 bricks | 1×1 round pieces
  1×2 plates | 1×2 bricks | Jumper plates
  Clips | Bars | Brackets
  Hinges | SNOT bricks | Small slopes
  Small curved pieces | Tiny transparent pieces | Small printed pieces
  Stud shooters and tiny special elements | Empty/overflow

Reply with ONLY the box name and compartment. Examples:
"Box 1 — Small: Technic pins"
"Box 2 — Big: Regular bricks"
"Box 3 — Small: Minifigure heads"
"Box 4 — Enormous: Standard bricks"
"Box 5 — Detail: 1×2 plates"
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
    api_key = os.environ.get("CEREBRAS_API_KEY") or config.CEREBRAS_API_KEY
    if not api_key:
        return "Box 5 — Detail: Empty/overflow"

    client = OpenAI(
        api_key=api_key,
        base_url=config.CEREBRAS_API_BASE,
    )

    try:
        response = client.chat.completions.create(
            model=config.CEREBRAS_MODEL,
            messages=[
                {"role": "system", "content": SORT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Part name: {part_name}, Part ID: {part_id}"},
            ],
            temperature=0.0,
            max_tokens=500,
        )
        msg = response.choices[0].message
        text = msg.content or msg.reasoning or ""
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


def classify(part_name, part_id):
    result = classify_part(part_name, part_id)
    box, compartment = parse_sort_result(result)
    cavity = lookup_cavity(box, compartment)
    return result, box, compartment, cavity
