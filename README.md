# SafetyX Pro – AI-Powered CCTV Safety Monitoring Platform

SafetyX Pro by The Brave Next Ltd transforms existing CCTV cameras into real-time AI safety monitoring systems for PPE detection, hazard alerts, restricted-area monitoring, and compliance reporting.

<p align="center">
  <img src="docs/assets/demo.gif" alt="SafetyX Pro Demo" width="100%">
</p>

---

## Overview

SafetyX Pro is an AI-powered industrial safety monitoring platform that converts traditional CCTV infrastructure into intelligent real-time safety systems. It detects PPE violations, unsafe behavior, fire/smoke risks, restricted-area breaches, and operational hazards without requiring new camera hardware.

Built for industrial environments, SafetyX Pro helps organizations improve compliance, reduce incidents, and respond proactively through AI-driven monitoring, alerts, and analytics.

---

## Key Features

- Real-time PPE detection (Helmet, Vest, Mask, Gloves)
- Unsafe behavior monitoring
- Fire and smoke detection
- Restricted-area intrusion alerts
- Live multi-camera monitoring dashboard
- Smart alert notifications with snapshots
- Compliance analytics and reporting
- Truck inspection monitoring
- Role-based dashboard interface
- CCTV integration without new hardware

---

## Demo Preview

The demo below shows SafetyX Pro detecting PPE violations, monitoring camera feeds, and generating live compliance alerts in real time.

---

## Tech Stack

### Backend
- FastAPI
- SQLAlchemy
- SQLite / PostgreSQL
- Pydantic
- OpenCV
- Ultralytics YOLO

### Frontend
- Jinja2 Templates
- HTML5
- CSS3
- JavaScript
- Chart.js

### AI / Vision
- YOLO-based detection models
- OpenCV video pipeline
- Multi-camera stream processing
- Real-time violation snapshot engine

---

## Project Structure

```bash
SafetyX-Pro/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── routes/
│   │       └── api.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── user.py
│   │   ├── camera.py
│   │   └── analytics.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── camera.py
│   │   └── analytics.py
│   ├── services/
│   │   ├── detector.py
│   │   ├── video_processor.py
│   │   └── analytics.py
│   ├── templates/
│   ├── static/
│   ├── utils/
│   │   └── logger.py
│   └── main.py
│
├── docs/
│   └── assets/
│       └── demo.gif
│
├── scripts/
│   ├── seed.py
│   └── check_cameras.py
│
├── tests/
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── requirements.txt
└── README.md
```

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/thebravenext/Safety.git
cd Safety
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Environment

#### Windows
```bash
venv\Scripts\activate
```

#### Linux / Mac
```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

Create `.env` file:

```env
DATABASE_URL=sqlite:///./safetyx.db
SECRET_KEY=change-this-in-production
PPE_MODEL_PATH=data/models/PPE_Model.pt
TRUCK_MODEL_PATH=data/models/truck.pt
FIRE_MODEL_PATH=data/models/fire.pt
```

### 6. Run Application

```bash
uvicorn app.main:app --reload
```

Open browser:

```text
http://127.0.0.1:8000
```

---

## Docker Setup

```bash
docker-compose up --build
```

---

## Default Login

```text
Email: admin@example.com
Password: admin123
```

---

## Use Cases

- Manufacturing safety compliance
- Construction PPE monitoring
- Warehouse worker monitoring
- Oil & gas hazard detection
- Smart industrial surveillance
- Truck loading / unloading inspection
- Fire and smoke alert systems

---

## Roadmap

- Role-based access control
- Mobile alert app
- WhatsApp alert integration
- Cloud analytics dashboard
- Multi-site enterprise management
- AI incident prediction
- API integrations for ERP / HSE systems

---

## Screenshots

Add product screenshots inside:

```text
docs/assets/screenshots/
```

Then reference them in this README.

---

## Contributing

Contributions, improvements, and enterprise integrations are welcome.

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push branch
5. Open pull request

---

## License

This project is proprietary software by The Brave Next Ltd.

© The Brave Next Ltd. All rights reserved.

---

## Company

**The Brave Next Ltd**  
AI for Industrial Safety, Automation, and Computer Vision

- Website: https://thebravenext.com
- Product: https://thesafetyxpro.com
- Email: najam@thebravenext.com

---
