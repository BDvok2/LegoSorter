import cv2
import requests
import time

import config
import groups
import color_detect


def load_image():
    frame = cv2.imread(config.IMAGE_FILE)

    if frame is None:
        print("Failed to load image:", config.IMAGE_FILE)
        return None

    return frame


def send_to_api():
    try:
        start = time.time()

        with open(config.IMAGE_FILE, "rb") as img:
            response = requests.post(
                config.API_URL,
                headers={"accept": "application/json"},
                files={
                    "query_image": (
                        "image.jpg",
                        img,
                        "image/jpeg"
                    )
                },
                timeout=config.REQUEST_TIMEOUT
            )

        response.raise_for_status()

        print(f"API time: {time.time() - start:.2f}s")

        return response.json()

    except Exception as e:
        print("API error:", e)
        return None


def detect():
    frame = load_image()
    if frame is None:
        return

    data = send_to_api()
    if not data or not data.get("items"):
        print("No part detected.")
        return

    part = data["items"][0]
    score = part.get("score", 0)

    if score < config.CONFIDENCE_THRESHOLD:
        print(f"Low confidence: {score:.2f}")
        return

    part_id = part["id"]
    part_name = part["name"]

    group = groups.groupof(part_id)

    color = color_detect.detect_color(
        frame,
        data["bounding_box"]
    )

    print("\n===== LEGO RESULT =====")
    print("Part:", part_name)
    print("ID:", part_id)
    print("Group:", group)
    print("Color:", color)
    print("=======================\n")


if __name__ == "__main__":
    detect()
