# SafetyX Pro – AI-Powered CCTV Safety Monitoring Platform

SafetyX Pro by **The Brave Next Ltd** transforms existing CCTV/IP cameras into real-time AI safety monitoring systems for PPE compliance, hazard alerts, restricted-area monitoring, camera dashboards, and safety reports.

![SafetyX Pro Demo](docs/assets/demo.gif)

> Replace `docs/assets/demo.gif` with your real recorded demo GIF before publishing publicly.

---

## Key Features

- Real-time camera stream monitoring
- PPE detection and missing PPE alerts
- Fire/smoke/truck-inspection model support structure
- Multi-camera dashboard
- Login/signup session flow
- Live MJPEG stream endpoint
- Notifications and reports pages
- SQLite default database, environment-based configuration
- Docker and CI-ready project structure

---

## Professional Folder Structure

```text
SafetyX-Pro/
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   │           └── health.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── database.py
│   │   └── crud.py
│   ├── models/
│   │   └── models.py
│   ├── schemas/
│   │   └── schemas.py
│   ├── services/
│   │   └── video_processor.py
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   ├── images/
│   │   ├── uploads/
│   │   └── violations/
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── camera.html
│   │   ├── camera_feed.html
│   │   ├── notifications.html
│   │   ├── reports.html
│   │   ├── login.html
│   │   └── signup.html
│   ├── utils/
│   │   └── logger.py
│   └── main.py
├── data/
│   ├── models/
│   ├── raw/
│   └── processed/
├── docs/
│   ├── assets/
│   │   └── demo.gif
│   └── setup.md
├── scripts/
│   ├── detector_preview.py
│   └── check_camera_sources.py
├── tests/
│   └── test_app.py
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone repository

```bash
git clone https://github.com/thebravenext/Safety.git
cd Safety
```

### 2. Create environment

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Add your YOLO weights here:

```text
data/models/PPE_Model.pt
```

### 5. Run application

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Default login:

```text
Email: admin@example.com
Password: admin123
```

---

## Docker Run

```bash
docker compose up --build
```

---

## API Health Check

```bash
GET /api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "SafetyX Pro"
}
```

---

## Demo GIF Setup

The README already includes:

```md
![SafetyX Pro Demo](docs/assets/demo.gif)
```

To add your real demo:

1. Record your dashboard demo video.
2. Convert it to GIF.
3. Save it as:

```text
docs/assets/demo.gif
```

Recommended FFmpeg command:

```bash
ffmpeg -i demo.mp4 -vf "fps=12,scale=900:-1:flags=lanczos" docs/assets/demo.gif
```

---

## GitHub Upload Recommendation

Do not upload heavy files directly:

- `.pt` model files
- `.mp4` demo videos
- database files
- `.env` secrets

Use GitHub Releases, Google Drive, or cloud storage for large model weights and demo videos.

---

## Suggested GitHub Topics

```text
computer-vision, safety-ai, ppe-detection, industrial-safety, cctv, fastapi, yolov8, workplace-safety
```

---

## Company

Built by **The Brave Next Ltd**.

Website: https://thebravenext.com  
Product: SafetyX Pro
