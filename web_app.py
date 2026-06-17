import cv2
import numpy as np
import requests
import json
import os
import time
import uuid
from dotenv import load_dotenv
import csv
import io
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn
import sort

load_dotenv()

API_URL = os.getenv("API_URL", "https://api.brickognize.com/internal/search/?external_catalogs=bricklink&predict_color=true")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "5"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))

API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://brickognize.com/",
    "Origin": "https://brickognize.com",
}

app = FastAPI()

DATA_DIR = "data"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, DATA_DIR, "photos")
PARTS_FILE = os.path.join(BASE_DIR, DATA_DIR, "parts.json")

os.makedirs(PHOTOS_DIR, exist_ok=True)

if not os.path.exists(PARTS_FILE):
    with open(PARTS_FILE, "w") as f:
        f.write("[]")


def merge_duplicates():
    with open(PARTS_FILE, "r") as f:
        parts = json.load(f)
    merged = {}
    seen_order = []
    for p in parts:
        key = (p["part_id"], p.get("color", ""))
        if key in merged:
            merged[key]["count"] = merged[key].get("count", 1) + 1
        else:
            p.setdefault("count", 1)
            merged[key] = p
            seen_order.append(key)
    ordered = [merged[k] for k in seen_order]
    with open(PARTS_FILE, "w") as f:
        json.dump(ordered, f, indent=2)


merge_duplicates()


def load_parts():
    with open(PARTS_FILE, "r") as f:
        parts = json.load(f)
    for p in parts:
        p.setdefault("count", 1)
        cav = p.get("cavity")
        if not cav or not isinstance(cav, int) or cav > 5:
            _, box, comp, cavity = sort.classify(p["part_name"], p["part_id"])
            p["box"] = box
            p["compartment"] = comp
            p["cavity"] = cavity
    save_parts(parts)
    return parts


def save_parts(parts):
    with open(PARTS_FILE, "w") as f:
        json.dump(parts, f, indent=2)


def find_part_by_id_color(parts, part_id, color):
    for i, p in enumerate(parts):
        if p["part_id"] == part_id and p.get("color", "") == (color or ""):
            return i, p
    return None, None


app.mount("/data/photos", StaticFiles(directory=PHOTOS_DIR), name="photos")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", "r") as f:
        return f.read()


@app.get("/api/parts")
async def get_parts():
    return JSONResponse(load_parts())


COLOR_MAP = {
    "Black": 0, "Blue": 1, "Green": 2, "Red": 4, "Brown": 6,
    "Dark Red": 320, "Dark Blue": 272, "Dark Green": 288, "Dark Brown": 308,
    "Dark Tan": 28, "Dark Purple": 85, "Dark Azure": 321, "Dark Bluish Gray": 72,
    "Flat Silver": 179, "Light Bluish Gray": 71, "Light Nougat": 78, "Lime": 27,
    "Medium Azure": 322, "Medium Blue": 73, "Medium Nougat": 84,
    "Metallic Silver": 80, "Nougat": 92, "Orange": 25, "Pearl Gold": 297,
    "Reddish Brown": 70, "Sand Blue": 379, "Tan": 19, "White": 15, "Yellow": 14,
    "Bright Green": 10, "Trans-Brown": 40, "Trans-Clear": 47, "Trans-Dark Blue": 33,
    "Trans-Green": 34, "Trans-Light Blue": 41, "Trans-Neon Green": 42,
    "Trans-Neon Orange": 57, "Trans-Orange": 182, "Trans-Red": 36, "Trans-Yellow": 46,
}

@app.get("/api/parts/export/rebrickable")
async def export_rebrickable():
    parts = load_parts()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Part", "Color", "Quantity"])
    for p in parts:
        color = p.get("color", "")
        if color and color not in COLOR_MAP:
            continue
        color_id = COLOR_MAP.get(color, "")
        writer.writerow([p["part_id"], color_id, p.get("count", 1)])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=rebrickable_export.csv"},
    )


@app.delete("/api/parts/{part_uid}")
async def delete_part(part_uid: str):
    parts = load_parts()
    parts = [p for p in parts if p["uid"] != part_uid]
    save_parts(parts)
    return JSONResponse({"ok": True})


@app.post("/api/adjust-count")
async def adjust_count(uid: str = Form(""), delta: int = Form(1)):
    parts = load_parts()
    for p in parts:
        if p["uid"] == uid:
            p["count"] = max(0, p.get("count", 1) + delta)
            if p["count"] == 0:
                parts = [x for x in parts if x["uid"] != uid]
            save_parts(parts)
            return JSONResponse({"ok": True, "count": p.get("count", 0) if p.get("count", 0) > 0 else 0})
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.post("/api/detect")
async def detect(file: UploadFile = File(...)):
    try:
        contents = await file.read()

        response = requests.post(
            API_URL,
            headers=API_HEADERS,
            files={"query_image": ("image.jpg", contents, "image/jpeg")},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("detected_items"):
            return JSONResponse({"error": "No part detected"})

        det = data["detected_items"][0]
        candidates = det.get("candidate_items", [])
        if not candidates:
            return JSONResponse({"error": "No part detected"})

        part = candidates[0]
        score = part.get("score", 0)

        if score < CONFIDENCE_THRESHOLD:
            return JSONResponse({"error": f"Low confidence: {score:.2f}"})

        part_id = part["id"].replace("part-", "")
        part_name = part["name"]

        colors = part.get("candidate_colors", [])
        color = colors[0]["name"] if colors else None

        sort_result, box, compartment, cavity = sort.classify(part_name, part_id)

        existing_count = 0
        existing_parts = load_parts()
        for ep in existing_parts:
            if ep["part_id"] == part_id and ep.get("color", "") == (color or ""):
                existing_count = ep.get("count", 1)
                break

        bbox_raw = det.get("bounding_boxes", [{}])[0]
        bbox = None
        if bbox_raw.get("left") is not None:
            bbox = {
                "left": bbox_raw["left"],
                "upper": bbox_raw["upper"],
                "right": bbox_raw["right"],
                "lower": bbox_raw["lower"],
                "image_width": bbox_raw.get("image_width"),
                "image_height": bbox_raw.get("image_height"),
            }

        return JSONResponse({
            "part_name": part_name,
            "part_id": part_id,
            "color": color,
            "confidence": score,
            "sort_result": sort_result,
            "box": box,
            "compartment": compartment,
            "cavity": cavity,
            "bbox": bbox,
            "existing_count": existing_count,
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/save")
async def save_part(
    file: UploadFile = File(...),
    part_id: str = Form(""),
    part_name: str = Form(""),
    color: str = Form(""),
    box: str = Form(""),
    compartment: str = Form(""),
    cavity: int = Form(0),
    bbox_left: float = Form(None),
    bbox_upper: float = Form(None),
    bbox_right: float = Form(None),
    bbox_lower: float = Form(None),
):
    try:
        contents = await file.read()

        if all(v is not None for v in [bbox_left, bbox_upper, bbox_right, bbox_lower]):
            nparr = np.frombuffer(contents, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is not None:
                h, w = frame.shape[:2]
                x1 = max(0, int(bbox_left))
                y1 = max(0, int(bbox_upper))
                x2 = min(w, int(bbox_right))
                y2 = min(h, int(bbox_lower))
                if x2 > x1 and y2 > y1:
                    cropped = frame[y1:y2, x1:x2]
                    _, buf = cv2.imencode('.jpg', cropped)
                    contents = buf.tobytes()

        ts = int(time.time() * 1000)
        uid = str(uuid.uuid4())[:8]
        photo_name = f"{ts}_{part_id}.jpg"
        photo_path = os.path.join(PHOTOS_DIR, photo_name)

        with open(photo_path, "wb") as f:
            f.write(contents)

        parts = load_parts()
        idx, existing = find_part_by_id_color(parts, part_id, color)

        if existing is not None:
            existing["count"] = existing.get("count", 1) + 1
            existing["photo"] = photo_name
            if color:
                existing["color"] = color
            existing["created"] = ts
            uid = existing["uid"]
        else:
            entry = {
                "uid": uid,
                "part_id": part_id,
                "part_name": part_name,
                "color": color,
                "count": 1,
                "box": box,
                "compartment": compartment,
                "cavity": cavity,
                "photo": photo_name,
                "created": ts,
            }
            parts.insert(0, entry)

        save_parts(parts)
        return JSONResponse({"ok": True, "uid": uid, "merged": existing is not None})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
