PART_GROUPS = {
    "2540": "Plates",
    "3001": "Bricks",
    "3002": "Bricks",
    "3022": "Plates",
    "3069": "Tiles",
}


def groupof(part_id):
    return PART_GROUPS.get(str(part_id), "Unknown")
