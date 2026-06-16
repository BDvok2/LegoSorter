import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "https://api.brickognize.com/predict/")

IMAGE_FILE = os.getenv("IMAGE_FILE", "assets/test.jpg")

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "5"))

KMEANS_CLUSTERS = int(os.getenv("KMEANS_CLUSTERS", "3"))

MIN_VALID_PIXELS = int(os.getenv("MIN_VALID_PIXELS", "50"))

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "gpt-oss-120b")
CEREBRAS_API_BASE = os.getenv("CEREBRAS_API_BASE", "https://api.cerebras.ai/v1")
