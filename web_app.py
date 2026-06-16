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

API_URL = os.getenv("API_URL", "https://api.brickognize.com/predict/")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "5"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))

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
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return JSONResponse({"error": "Failed to decode image"}, status_code=400)

        _, img_encoded = cv2.imencode('.jpg', frame)
        img_bytes = img_encoded.tobytes()

        response = requests.post(
            API_URL,
            headers={"accept": "application/json"},
            files={"query_image": ("image.jpg", img_bytes, "image/jpeg")},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("items"):
            return JSONResponse({"error": "No part detected"})

        part = data["items"][0]
        score = part.get("score", 0)

        if score < CONFIDENCE_THRESHOLD:
            return JSONResponse({"error": f"Low confidence: {score:.2f}"})

        part_id = part["id"]
        part_name = part["name"]

        sort_result, box, compartment, cavity = sort.classify(part_name, part_id)

        return JSONResponse({
            "part_name": part_name,
            "part_id": part_id,
            "confidence": score,
            "sort_result": sort_result,
            "box": box,
            "compartment": compartment,
            "cavity": cavity,
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/save")
async def save_part(
    file: UploadFile = File(...),
    part_id: str = Form(""),
    part_name: str = Form(""),
    box: str = Form(""),
    compartment: str = Form(""),
    cavity: str = Form(""),
):
    try:
        contents = await file.read()
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
