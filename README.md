# ✦ OPSHE Beauty AI — Virtual Skin Analyzer

> AI-powered skin analysis across **13 parameters** with personalized ingredient-based skincare recommendations — no brand names, ever.

---

## Overview

OPSHE Beauty AI is a full-stack web application that analyzes facial skin condition using computer vision and AI, then generates a personalized skincare routine with active ingredient recommendations tailored to the user's unique skin profile.

### Key Features

- **Live camera capture** or **photo upload**
- **Face detection** via MediaPipe Face Mesh (single face enforcement)
- **13-parameter skin analysis** across 5 facial zones
- **Personalized morning & night routines** with active ingredients
- **No brand names** — only product types and ingredient recommendations
- **SQLite** database (dev) / **PostgreSQL** (prod) via SQLAlchemy
- **REST API** — fully decoupled frontend/backend
- **Railway-ready** deployment with Docker

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn |
| Computer Vision | OpenCV, MediaPipe Face Mesh |
| Image Processing | scikit-image, Pillow, NumPy |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | HTML5, CSS3, Vanilla JS, Bootstrap-compatible |
| Deployment | Docker, Railway, GitHub |

---

## Analysis Parameters

| # | Parameter | Details |
|---|-----------|---------|
| 1 | Skin Type | Oily / Dry / Combination / Normal + confidence |
| 2 | Oil Level | 0–100% |
| 3 | Dryness | 0–100% |
| 4 | Pore Visibility | 0–100% |
| 5 | Skin Texture | Smooth / Normal / Rough |
| 6 | Acne Detection | Acne / Whitehead / Blackhead / Acne Scar counts |
| 7 | Redness | 0–100% |
| 8 | Pigmentation | 0–100% |
| 9 | Dark Spots | Count |
| 10 | Dark Circles | None / Light / Medium / Heavy |
| 11 | Fine Lines | None / Mild / Moderate / Severe |
| 12 | Skin Tone | Fair / Light / Medium / Tan / Deep |
| 13 | Undertone | Cool / Warm / Neutral |

**Zones analyzed:** Forehead · Nose · Left Cheek · Right Cheek · Chin

---

## Project Structure

```
opshe/
├── backend/
│   ├── api/
│   │   └── routes.py          # FastAPI route handlers
│   ├── config/
│   │   └── settings.py        # Environment-based configuration
│   ├── database/
│   │   └── db.py              # SQLAlchemy models + session
│   ├── models/
│   │   └── schemas.py         # Pydantic schemas
│   ├── services/
│   │   ├── face_detection.py  # MediaPipe face detection
│   │   ├── skin_analyzer.py   # Core analysis algorithms
│   │   └── analysis_orchestrator.py  # Pipeline coordinator
│   ├── utils/
│   │   └── image_processing.py  # Preprocessing utilities
│   └── main.py                # FastAPI app instance
├── ai/
│   └── recommendation_engine.py  # Ingredient KB + routine generator
├── frontend/
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/main.css
│       └── js/app.js
├── models/                    # AI model weights (empty — add yours)
├── logs/                      # Application logs
├── uploads/                   # Temporary image storage
├── run.py                     # Entry point
├── requirements.txt
├── Dockerfile
├── railway.json
├── Procfile
├── .env.example
└── .gitignore
```

---

## Local Installation

### Prerequisites

- Python 3.12+
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/opshe-beauty-ai.git
cd opshe-beauty-ai

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux / macOS
.venv\Scripts\activate          # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env as needed (defaults work for local dev)

# 5. Create required directories
mkdir -p logs uploads models

# 6. Run the server
python run.py
```

Open your browser at: **http://localhost:8000**

---

## API Endpoints

### `POST /analyze`
Analyze a skin image.

**Request:** `multipart/form-data` with `file` field (JPEG / PNG / WebP, max 10MB)

**Response:**
```json
{
  "session_id": "abc123",
  "skin_type": "Combination",
  "skin_type_confidence": 0.80,
  "oil_level": 62.3,
  "dryness": 18.7,
  "pore_visibility": 55.1,
  "skin_texture": "Normal",
  "acne_metrics": { "acne": 2, "whitehead": 0, "blackhead": 14, "acne_scar": 1 },
  "redness": 22.4,
  "pigmentation": 31.8,
  "dark_spot_count": 3,
  "dark_circle_level": "Light",
  "fine_lines_level": "Mild",
  "skin_tone": "Medium",
  "undertone": "Warm",
  "overall_score": 74.5,
  "zones": [...],
  "morning_routine": [...],
  "night_routine": [...],
  "recommendations": { ... }
}
```

### `GET /history?limit=10`
Retrieve past analysis sessions (most recent first).

### `GET /health`
Service health check.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable hot-reload and verbose logging |
| `SECRET_KEY` | — | App secret (change in production!) |
| `HOST` | `0.0.0.0` | Bind host |
| `PORT` | `8000` | Bind port |
| `DATABASE_URL` | `sqlite:///./opshe.db` | Database connection string |
| `MAX_IMAGE_SIZE_MB` | `10` | Maximum upload size |

---

## Deployment to Railway

### Option A — GitHub Integration (Recommended)

1. Push your code to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: OPSHE Beauty AI"
   git remote add origin https://github.com/yourusername/opshe-beauty-ai.git
   git push -u origin main
   ```

2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**

3. Select your repository → Railway auto-detects the `Dockerfile`

4. Add environment variables in Railway dashboard:
   - `DATABASE_URL` (use Railway's PostgreSQL plugin)
   - `SECRET_KEY`
   - `DEBUG=false`

5. Deploy — Railway provides a public URL automatically.

### Option B — Railway CLI

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Using PostgreSQL on Railway

1. In Railway dashboard → **New** → **Database** → **PostgreSQL**
2. Copy the `DATABASE_URL` from the PostgreSQL service
3. Set it as an environment variable in your app service
4. SQLAlchemy will automatically use PostgreSQL instead of SQLite — no code changes needed

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| `Camera access denied` | Allow camera permissions in browser settings |
| `No face detected` | Ensure face is well-lit and fully in frame |
| `Please capture only one face` | Only one person should be in the frame |
| `Image is too blurry` | Hold still, ensure good lighting, move closer |
| `Image is too dark` | Improve lighting or use a brighter environment |
| `mediapipe not found` | Run `pip install mediapipe==0.10.14` |
| `ModuleNotFoundError` | Ensure virtual environment is activated |
| Port already in use | Set `PORT=8001` in `.env` |
| SQLite locked (prod) | Switch to PostgreSQL via `DATABASE_URL` |

---

## Disclaimer

> Hasil analisis merupakan estimasi berbasis AI dari citra wajah dan tidak menggantikan diagnosis atau konsultasi dengan dokter kulit.
>
> *Analysis results are AI-based estimates from facial imagery and do not replace diagnosis or consultation with a dermatologist.*

---

## License

MIT License — See `LICENSE` for details.

---

*Built with ✦ by OPSHE Beauty AI*
