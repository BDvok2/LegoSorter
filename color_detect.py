import cv2
import numpy as np
import math
import config


LEGO_COLORS = {
    "White": (0, 0, 240),
    "Black": (0, 0, 30),
    "Light Bluish Gray": (110, 20, 160),
    "Dark Bluish Gray": (110, 30, 90),
    "Red": (0, 220, 180),
    "Blue": (115, 220, 180),
    "Yellow": (30, 230, 230),
    "Green": (60, 220, 140),
    "Tan": (20, 80, 200),
    "Brown": (10, 180, 80),
}


def hsv_distance(a, b):
    dh = min(abs(a[0] - b[0]), 180 - abs(a[0] - b[0]))
    ds = abs(a[1] - b[1])
    dv = abs(a[2] - b[2])

    return (dh**2 + ds**2 + dv**2) ** 0.5


def detect_color(frame, bbox):
    x1 = int(bbox["left"])
    y1 = int(bbox["upper"])
    x2 = int(bbox["right"])
    y2 = int(bbox["lower"])

    piece = frame[y1:y2, x1:x2]

    if piece.size == 0:
        return None

    hsv = cv2.cvtColor(piece, cv2.COLOR_BGR2HSV)

    pixels = hsv.reshape(-1, 3)
    pixels = pixels[pixels[:, 2] > 40]

    if len(pixels) < config.MIN_VALID_PIXELS:
        return None

    pixels = np.float32(pixels)

    _, labels, centers = cv2.kmeans(
        pixels,
        config.KMEANS_CLUSTERS,
        None,
        (
            cv2.TERM_CRITERIA_EPS +
            cv2.TERM_CRITERIA_MAX_ITER,
            20,
            1.0
        ),
        10,
        cv2.KMEANS_RANDOM_CENTERS
    )

    counts = np.bincount(labels.flatten())
    dominant = centers[np.argmax(counts)]

    best = None
    best_dist = float("inf")

    for name, color in LEGO_COLORS.items():
        d = hsv_distance(dominant, color)
        if d < best_dist:
            best_dist = d
            best = name

    return best
