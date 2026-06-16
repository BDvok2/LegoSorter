import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

IMAGE_FILE = os.getenv("IMAGE_FILE", "assets/test.jpg")
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


def send_to_api():
    try:
        start = time.time()

        with open(IMAGE_FILE, "rb") as img:
            response = requests.post(
                API_URL,
                headers=API_HEADERS,
                files={
                    "query_image": (
                        "image.jpg",
                        img,
                        "image/jpeg"
                    )
                },
                timeout=REQUEST_TIMEOUT
            )

        response.raise_for_status()

        print(f"API time: {time.time() - start:.2f}s")

        return response.json()

    except Exception as e:
        print("API error:", e)
        return None


def detect():
    data = send_to_api()
    if not data or not data.get("detected_items"):
        print("No part detected.")
        return

    det = data["detected_items"][0]
    candidates = det.get("candidate_items", [])
    if not candidates:
        print("No part detected.")
        return

    part = candidates[0]
    score = part.get("score", 0)

    if score < CONFIDENCE_THRESHOLD:
        print(f"Low confidence: {score:.2f}")
        return

    part_id = part["id"].replace("part-", "")
    part_name = part["name"]

    colors = part.get("candidate_colors", [])
    color = colors[0]["name"] if colors else None

    print("\n===== LEGO RESULT =====")
    print("Part:", part_name)
    print("ID:", part_id)
    print("Color:", color)
    print("=======================\n")


if __name__ == "__main__":
    detect()
