# LegoSorter

Identify LEGO parts from photos, detect their color, and sort them into storage boxes using AI.

## Features

- **Part recognition** via [Brickognize API](https://brickognize.com)
- **Color detection** using OpenCV k-means clustering
- **AI sorting** — classifies parts into boxes/cavities via an LLM (Cerebras / OpenAI-compatible)
- **Mobile web UI** — capture parts with your phone camera, review and save results
- **CLI mode** for testing with local images

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env — at minimum set CEREBRAS_API_KEY
```

### Web app

```bash
python web_app.py
```

Open `http://localhost:8080` — point your camera at a LEGO part and tap capture.

### CLI

```bash
python main.py
```

Uses `assets/test.jpg` by default (override with `IMAGE_FILE` env var).

## Configuration

All settings are environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `API_URL` | `https://api.brickognize.com/predict/` | Brickognize endpoint |
| `CONFIDENCE_THRESHOLD` | `0.5` | Minimum detection confidence |
| `REQUEST_TIMEOUT` | `5` | API request timeout (seconds) |
| `KMEANS_CLUSTERS` | `3` | Color quantization clusters |
| `MIN_VALID_PIXELS` | `50` | Minimum pixels for color detection |
| `CEREBRAS_API_KEY` | — | LLM API key for sorting |
| `CEREBRAS_MODEL` | `gpt-oss-120b` | LLM model name |
| `CEREBRAS_API_BASE` | `https://api.cerebras.ai/v1` | LLM API base URL |

## Deploy on Render

1. Create a new **Web Service** on Render
2. Set **Build Command** to `pip install -r requirements.txt`
3. Set **Start Command** to `python web_app.py`
4. Add all env vars from `.env.example` in the Render dashboard
5. Deploy

## Project structure

```
├── web_app.py         # FastAPI web server
├── main.py            # CLI entry point
├── color_detect.py    # Color detection via k-means
├── sort.py            # LLM-based part sorting
├── templates/         # Web frontend
└── data/              # Saved parts & photos
```
