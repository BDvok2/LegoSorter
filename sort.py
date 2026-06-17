from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


CATEGORIES = {
    1: "Basic Bricks",
    2: "Plates & Tiles",
    3: "SNOT & Brackets",
    4: "Walls, Panels, Doors & Windows",
    5: "Slopes, Wedges & Angles",
    6: "Curves & Round Parts",
    7: "Hinges, Clips, Bars & Ball Joints",
    8: "Technic Structure",
    9: "Technic Connectors",
    10: "Technic Motion",
    11: "Vehicle Wheels & Chassis",
    12: "Vehicle Specialized",
    13: "Minifig Bodies",
    14: "Minifig Accessories",
    15: "Nature & Animals",
    16: "Electronics / Powered Up",
    17: "Printed / Decorated Parts",
    18: "Flexible Parts",
    19: "Large Specialized Parts",
    20: "Unknown / Miscellaneous",
}


KEYWORDS = {
    1: [
        "brick", "hollow brick", "modified brick", "1x1 brick", "2x2 brick",
        "1 x 1 brick", "2 x 2 brick", "headlight brick",
    ],
    2: [
        "plate", "tile", "jumper", "jumper plate", "jumper tile", "slab",
    ],
     3: [
        "snot", "bracket", "side stud", "stud on side", "studs on side",
        "stud reversal", "offset", "stud",
        "headlight brick", "offset plate", "inverted bracket",
    ],
    4: [
        "wall", "panel", "door", "window", "frame", "fence", "arch",
    ],
    5: [
        "slope", "wedge", "angled", "inverted slope", "corner wedge",
        "double slope", "triple slope",
    ],
    6: [
        "curve", "curved", "dome", "dish", "cylinder", "cone", "round",
        "rounded", "tube",
    ],
    7: [
        "hinge", "clip", "bar", "ball joint", "ball socket", "socket",
        "tow ball",
        "joint", "swivel", "ratchet",
        "finger joint", "click hinge",
    ],
    8: [
        "technic beam", "beam", "liftarm", "technic frame", "technic brick",
        "technic structure", "frame technic", "hole",
    ],
    9: [
        "pin", "axle", "bushing", "connector", "joiner", "pin connector",
        "axle connector", "friction pin", "pin with friction",
    ],
    10: [
        "gear", "pulley", "turntable", "actuator", "linear actuator",
        "steering", "suspension", "chain", "track mechanism", "worm gear",
        "bevel gear",
    ],
    11: [
        "wheel", "tire", "tyre", "rim", "mudguard", "chassis", "wheel arch",
        "tread",
    ],
    12: [
        "cockpit", "windscreen", "windshield", "propeller", "boat hull",
        "hull", "train", "rail", "track", "ski", "aircraft", "plane",
        "fuselage", "wing",
    ],
    13: [
        "minifig", "minifigure", "head", "torso", "legs", "hips", "hair",
        "hat", "helmet", "neckwear", "cape", "arm",
    ],
    14: [
        "tool", "weapon", "backpack", "armor", "accessory", "container",
        "shield", "sword", "blaster", "gun", "camera", "book", "utensil",
        "broom", "cup",
    ],
    15: [
        "plant", "leaf", "flower", "tree", "animal", "bone", "horn", "claw",
        "tail", "shell", "rock", "crystal", "root", "vine",
    ],
    16: [
        "motor", "battery", "battery box", "hub", "sensor", "light", "switch",
        "wire", "powered up", "control+", "controller",
    ],
    17: [
        "printed", "print", "sticker", "decorated", "pattern", "patterned",
        "patter",
    ],
    18: [
        "rubber", "string", "chain", "fabric", "cloth", "hose", "flex",
        "flexible", "rope", "band",
    ],
    19: [
        "large specialized", "specialized", "big molded", "one-off", "molded",
        "giant", "custom mold",
    ],
}


CAVITY_LAYERS = {
    1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1,
    7: 2, 8: 2, 9: 2, 10: 2, 11: 2, 12: 2,
    13: 3, 14: 3, 15: 3, 16: 3, 17: 3, 18: 3, 19: 3, 20: 3,
}

SHAPE_WORDS = [
    "plate", "brick", "tile", "slope", "wedge", "round", "curved",
    "cone", "dome", "dish", "cylinder", "panel", "door", "window",
    "arch", "wall", "fence",
]

FEATURE_WORDS = [
    "bar", "beam", "liftarm", "hinge", "clip", "bracket", "snot",
    "offset", "pin", "axle", "hole", "gear", "wheel", "tire",
    "socket", "ball joint", "tow ball",
]


HARD_RULES: List[Tuple[int, List[str]]] = [
    (16, ["motor", "battery box", "hub", "sensor", "powered up", "control+"]),
    (13, ["torso", "hips", "legs", "head", "hair", "helmet"]),
    (14, ["backpack", "armor", "tool", "weapon", "shield", "accessory", "container"]),
    (18, ["rubber band", "string", "fabric", "cloth", "rope", "hose"]),
]


def _normalize(text: str) -> str:
    text = text.lower()
    text = text.replace("\u00d7", "x")
    text = re.sub(r"[_/\\\-]+", " ", text)
    text = re.sub(r"[^\w\s+]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _specs_to_text(specs: Any) -> str:
    if specs is None:
        return ""
    if isinstance(specs, str):
        return specs
    if isinstance(specs, dict):
        parts = []
        for k, v in specs.items():
            if v is None:
                continue
            if isinstance(v, (list, tuple, set)):
                v = " ".join(map(str, v))
            parts.append(f"{k}: {v}")
        return " | ".join(parts)
    return str(specs)


def _in_text(phrase: str, text: str) -> bool:
    if re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', text):
        return True
    if phrase.endswith(('sh', 'ch', 's', 'x', 'z')):
        plural = phrase + 'es'
    elif phrase.endswith('y') and len(phrase) > 2 and phrase[-2] not in 'aeiou':
        plural = phrase[:-1] + 'ies'
    elif not phrase.endswith('s'):
        plural = phrase + 's'
    else:
        return False
    return bool(re.search(r'(?<!\w)' + re.escape(plural) + r'(?!\w)', text))


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    return any(_in_text(p, text) for p in phrases)


def _count_hits(text: str, phrases: Iterable[str]) -> int:
    return sum(1 for p in phrases if _in_text(p, text))


def _first_word_in(text: str, phrases: Iterable[str]) -> bool:
    first = text.split()[0] if text else ""
    return any(_in_text(p, first) for p in phrases)


@dataclass
class ClassificationResult:
    part_name: str
    part_number: Optional[str]
    normalized_name: str
    normalized_text: str
    attributes: Dict[str, Any]
    category: Dict[str, Any]


def extract_attributes(part_name: str, specs: Any = None, part_number: Optional[str] = None) -> Dict[str, Any]:
    text = _normalize(f"{part_name} {part_number or ''} {_specs_to_text(specs)}")

    def flag(*phrases: str) -> bool:
        return _contains_any(text, phrases)

    attributes = {
        "likely_system": "unknown",
        "geometry_type": "unknown",
        "connection_type": "unknown",
        "scale_family": "unknown",
        "decoration_status": "unknown",
        "material_hint": "unknown",
        "moving_part_hint": False,
        "vehicle_hint": False,
        "minifig_hint": False,
    }

    if flag("technic"):
        attributes["likely_system"] = "technic"
    elif flag("minifig", "minifigure"):
        attributes["likely_system"] = "minifig"
    elif flag("duplo"):
        attributes["likely_system"] = "duplo"
    elif flag("power functions", "powered up", "control+", "motor", "sensor", "hub", "battery"):
        attributes["likely_system"] = "electronics"
    elif flag("train", "rail", "track", "boat", "hull", "propeller", "aircraft", "plane"):
        attributes["likely_system"] = "vehicle_specialized"
    elif flag("wheel", "tire", "tyre", "mudguard", "chassis", "cockpit"):
        attributes["likely_system"] = "vehicle"

    if flag("brick"):
        attributes["geometry_type"] = "brick-like"
    elif flag("plate", "tile", "jumper"):
        attributes["geometry_type"] = "flat"
    elif flag("slope", "wedge", "angled"):
        attributes["geometry_type"] = "angled"
    elif flag("curve", "curved", "dome", "dish", "cone", "cylinder", "round"):
        attributes["geometry_type"] = "curved"
    elif flag("hinge", "clip", "bar", "ball joint", "joint"):
        attributes["geometry_type"] = "articulation"
    elif flag("beam", "liftarm", "pin", "axle", "bushing", "connector", "gear", "pulley"):
        attributes["geometry_type"] = "technic"

    if flag("stud", "plate", "tile", "brick"):
        attributes["connection_type"] = "stud-based"
    if flag("pin", "axle", "connector", "bushing"):
        attributes["connection_type"] = "technic-connection"
    if flag("clip", "bar", "hinge", "ball joint"):
        attributes["connection_type"] = "articulated"

    if flag("printed", "print", "sticker", "decorated", "pattern"):
        attributes["decoration_status"] = "decorated"
    if flag("rubber", "string", "fabric", "cloth", "rope", "hose"):
        attributes["material_hint"] = "flexible"
    if flag("metal"):
        attributes["material_hint"] = "metal-like"
    if flag("transparent", "trans-clear", "clear", "translucent"):
        attributes["material_hint"] = "transparent"

    attributes["moving_part_hint"] = flag("hinge", "joint", "swivel", "ratchet", "turntable", "actuator", "motor")
    attributes["vehicle_hint"] = flag("wheel", "tire", "tyre", "mudguard", "chassis", "cockpit", "train", "boat", "propeller", "ski")
    attributes["minifig_hint"] = flag("minifig", "minifigure", "torso", "legs", "hips", "head", "hair", "helmet", "cape")

    return attributes


def score_categories(part_name: str, specs: Any = None, part_number: Optional[str] = None) -> Dict[int, int]:
    text = _normalize(f"{part_name} {part_number or ''} {_specs_to_text(specs)}")

    scores = {i: 0 for i in range(1, 21)}

    for cavity, phrases in HARD_RULES:
        if cavity == 13:
            if _first_word_in(text, phrases):
                scores[cavity] += 1000
        else:
            if _contains_any(text, phrases):
                scores[cavity] += 1000

    for cavity, phrases in KEYWORDS.items():
        hits = _count_hits(text, phrases)
        if hits:
            scores[cavity] += hits * 10

    if _contains_any(text, ["printed", "sticker", "decorated", "pattern", "patter"]):
        scores[17] += 50
    if _contains_any(text, ["tile", "plate"]) and _contains_any(text, ["pattern", "patter", "printed", "decorated", "sticker"]):
        scores[17] += 30

    if _contains_any(text, ["rubber band", "string", "cloth", "fabric", "rope", "hose"]):
        scores[18] += 50

    if _contains_any(text, ["motor", "battery box", "hub", "sensor", "led", "switch", "wire", "powered up", "control+"]):
        scores[16] += 60

    if _contains_any(text, ["minifig", "minifigure"]):
        if _contains_any(text, ["head", "torso", "legs", "hips", "hair", "hat", "helmet", "neckwear", "cape", "arm"]):
            scores[13] += 70
        else:
            scores[14] += 50
    if "arm" in text and not _contains_any(text, SHAPE_WORDS + FEATURE_WORDS + ["technic"]):
        scores[13] += 50
    if _contains_any(text, ["backpack", "armor", "tool", "weapon", "shield", "accessory", "container", "sword", "blaster", "gun", "camera", "book", "utensil", "broom"]):
        scores[14] += 50
    if _contains_any(text, ["plant", "leaf", "flower", "tree", "animal", "bone", "horn", "claw", "tail", "shell", "rock", "crystal"]):
        scores[15] += 70

    if "technic" in text:
        scores[8] += 30
        scores[9] += 30
        scores[10] += 30

    if "tile" in text:
        scores[2] += 25
    if "plate" in text:
        scores[2] += 20
    if "brick" in text and "headlight brick" not in text:
        scores[1] += 20

    if _contains_any(text, ["slope", "wedge", "angled", "corner wedge"]):
        scores[5] += 50
        if _contains_any(text, ["curve", "curved"]):
            scores[5] += 20
        if "stud" in text:
            scores[5] += 20
    if _contains_any(text, ["curve", "curved", "dome", "dish", "cone", "cylinder", "round"]):
        scores[6] += 50
    if _contains_any(text, ["hinge", "clip", "bar", "ball joint", "ball socket", "socket", "tow ball", "joint", "swivel"]):
        scores[7] += 50
        if "hinge" in text and ("hole" in text or "axle" in text):
            scores[7] += 30
    if _contains_any(text, ["wall", "panel", "door", "window", "frame", "fence", "arch"]):
        scores[4] += 50
    if _contains_any(text, ["bracket", "snot", "side stud", "stud on side", "studs on side", "offset", "stud reversal", "headlight brick", "headlight", "stud", "studs"]):
        scores[3] += 50
    if _contains_any(text, ["beam", "liftarm", "frame", "technic brick", "hole"]):
        scores[8] += 50
    if _contains_any(text, ["brick", "plate"]) and _contains_any(text, ["pin", "axle"]):
        scores[8] += 30
    if _contains_any(text, ["pin", "axle", "bushing", "connector", "joiner", "friction pin"]):
        scores[9] += 50
    if _contains_any(text, ["gear", "pulley", "turntable", "actuator", "steering", "suspension", "chain"]):
        scores[10] += 50
    if _contains_any(text, ["wheel", "tire", "tyre", "rim", "mudguard", "chassis", "tread", "thread"]):
        scores[11] += 50
    if _contains_any(text, ["tread", "thread"]):
        scores[11] += 20
    if _contains_any(text, ["cockpit", "windscreen", "windshield", "propeller", "hull", "train", "rail", "track", "ski", "aircraft", "plane", "wing"]):
        scores[12] += 50

    return scores


def _layer_select(scores: Dict[int, int]) -> int:
    best = max(scores, key=lambda c: (scores[c], -c))
    layer = CAVITY_LAYERS.get(best, 3)
    if layer < 3 or scores[best] >= 80:
        return best
    best_l2 = max((c for c in range(7, 13)), key=lambda c: (scores.get(c, 0), -c), default=None)
    best_l1 = max((c for c in range(1, 7)), key=lambda c: (scores.get(c, 0), -c), default=None)
    s2 = scores.get(best_l2, 0) if best_l2 else 0
    s1 = scores.get(best_l1, 0) if best_l1 else 0
    if s2 > 0 and scores[best] < s2 * 2:
        return best_l2
    if s1 > 0 and scores[best] < s1 * 2:
        return best_l1
    return best


def classify_part(part_name: str, specs: Any = None, part_number: Optional[str] = None) -> ClassificationResult:
    normalized_name = _normalize(part_name)

    combined = f"{part_name} {part_number or ''} {_specs_to_text(specs)}"
    normalized_text = _normalize(combined)

    attributes = extract_attributes(part_name, specs, part_number)

    scores = score_categories(part_name, specs, part_number)
    best_cavity = _layer_select(scores)
    best_score = scores[best_cavity]

    sorted_scores = sorted(scores.values(), reverse=True)
    runner_up = sorted_scores[1] if len(sorted_scores) > 1 else 0
    confidence = 0.15

    if best_score >= 1000:
        confidence = 0.99
    elif best_score >= 80:
        confidence = 0.90 if best_score - runner_up >= 30 else 0.75
    elif best_score >= 40:
        confidence = 0.70 if best_score - runner_up >= 20 else 0.55
    elif best_score >= 20:
        confidence = 0.45
    else:
        best_cavity = 20
        confidence = 0.20

    reason = _build_reason(normalized_text, best_cavity, scores)

    return ClassificationResult(
        part_name=part_name,
        part_number=part_number,
        normalized_name=normalized_name,
        normalized_text=normalized_text,
        attributes=attributes,
        category={
            "cavity": _flat_to_local(best_cavity),
            "flat_cavity": best_cavity,
            "box": _cavity_to_box(best_cavity),
            "name": CATEGORIES[best_cavity],
            "confidence": round(confidence, 2),
            "reason": reason,
            "scores": scores,
        },
    )


def _build_reason(text: str, cavity: int, scores: Dict[int, int]) -> str:
    clues_by_cavity = {
        1: ["brick", "hollow brick", "modified brick"],
        2: ["plate", "tile", "jumper"],
        3: ["bracket", "snot", "side stud", "offset", "headlight brick"],
        4: ["wall", "panel", "door", "window", "frame", "fence", "arch"],
        5: ["slope", "wedge", "angled"],
        6: ["curve", "curved", "dome", "dish", "cone", "cylinder", "round"],
        7: ["hinge", "clip", "bar", "ball joint", "joint", "swivel"],
        8: ["technic", "beam", "liftarm", "frame"],
        9: ["pin", "axle", "bushing", "connector", "joiner"],
        10: ["gear", "pulley", "turntable", "actuator", "steering", "suspension", "chain"],
        11: ["wheel", "tire", "tyre", "rim", "mudguard", "chassis"],
        12: ["train", "track", "boat", "hull", "propeller", "ski", "cockpit"],
        13: ["minifig", "head", "torso", "legs", "hips", "hair", "helmet"],
        14: ["tool", "weapon", "backpack", "armor", "accessory", "container"],
        15: ["plant", "animal", "bone", "horn", "claw", "tail", "wing", "shell", "rock", "crystal"],
        16: ["motor", "battery", "hub", "sensor", "light", "switch", "wire"],
        17: ["printed", "sticker", "decorated", "pattern"],
        18: ["rubber", "string", "chain", "fabric", "cloth", "hose"],
        19: ["specialized", "large", "molded", "custom"],
    }

    clues = [c for c in clues_by_cavity.get(cavity, []) if c in text]
    if not clues:
        return "No strong keyword match; used fallback logic."
    return f"Matched: {', '.join(clues[:3])}"


def _cavity_to_box(cavity: int) -> str:
    return str((cavity - 1) // 5 + 1)


def _flat_to_local(cavity: int) -> int:
    return ((cavity - 1) % 5) + 1


_CACHE: dict = {}


def classify(part_name: str, part_id: str = "") -> Tuple[str, str, str, int]:
    cache_key = f"{part_id}:{part_name}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    result = classify_part(part_name, part_number=part_id)
    flat_cav = result.category["flat_cavity"]
    name = result.category["name"]
    box = _cavity_to_box(flat_cav)
    local_cav = result.category["cavity"]
    reason = result.category["reason"]

    text = f"Box {box} \u2022 Cav {local_cav}: {name} [{reason}]"

    cached = (text, box, name, local_cav)
    _CACHE[cache_key] = cached
    return cached
