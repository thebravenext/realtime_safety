# Setup Guide

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Model Files

Place model files inside:

```text
data/models/
```

Example:

```text
data/models/PPE_Model.pt
```

## Camera Sources

Supported examples:

```text
0
C:/videos/demo.mp4
rtsp://username:password@192.168.1.10/stream1
```
