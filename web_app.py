import cv2
import numpy as np
import requests
import json
import os
import time
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
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


def load_parts():
    with open(PARTS_FILE, "r") as f:
        parts = json.load(f)
    for p in parts:
        if "cavity" not in p or not p["cavity"]:
            _, _, _, cavity = sort.classify(p["part_name"], p["part_id"])
            p["cavity"] = cavity
    return parts


def save_parts(parts):
    with open(PARTS_FILE, "w") as f:
        json.dump(parts, f, indent=2)


app.mount("/data/photos", StaticFiles(directory=PHOTOS_DIR), name="photos")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", "r") as f:
        return f.read()


@app.get("/api/parts")
async def get_parts():
    return JSONResponse(load_parts())


@app.delete("/api/parts/{part_uid}")
async def delete_part(part_uid: str):
    parts = load_parts()
    parts = [p for p in parts if p["uid"] != part_uid]
    save_parts(parts)
    return JSONResponse({"ok": True})


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
    cavity: str = Form(""),
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

        entry = {
            "uid": uid,
            "part_id": part_id,
            "part_name": part_name,
            "color": color,
            "box": box,
            "compartment": compartment,
            "cavity": cavity,
            "photo": photo_name,
            "created": ts,
        }

        parts = load_parts()
        parts.insert(0, entry)
        save_parts(parts)

        return JSONResponse({"ok": True, "uid": uid})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
