from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER

from app.db import crud
from app.models import models
from app.schemas import schemas
from app.db.database import SessionLocal, engine
from app.api.v1.router import api_router
from app.services.video_processor import (
    get_latest_frame_bytes,
    get_stream_statuses,
    start_all_camera_streams,
    start_camera_stream,
    stop_camera_stream,
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Industrial Safety AI Dashboard")

app.add_middleware(
    SessionMiddleware,
    secret_key="change-this-secret-key-before-production-123456",
    same_site="lax",
    max_age=60 * 60 * 24 * 7,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api_router)
templates = Jinja2Templates(directory="app/templates")

MODEL_OPTIONS = [
    {"value": "ppe", "label": "PPE Model"},
    {"value": "truck_inspection", "label": "Truck Inspection"},
    {"value": "fire_alert", "label": "Fire Alert"},
]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return crud.get_user_by_id(db, user_id)


def require_login(request: Request, db: Session):
    user = get_current_user(request, db)
    if not user:
        return None
    return user


@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        crud.ensure_default_user(db)
    finally:
        db.close()

    start_all_camera_streams()


def build_common_context(request: Request, db: Session, active_page: str, user):
    cameras = crud.get_user_cameras(db, user.id)
    stream_states = get_stream_statuses()

    camera_cards = []
    for cam in cameras:
        state = stream_states.get(cam.id, {})
        camera_cards.append(
            {
                "id": cam.id,
                "name": cam.name,
                "source": cam.source,
                "selected_model": cam.selected_model,
                "selected_model_label": {
                    "ppe": "PPE Model",
                    "truck_inspection": "Truck Inspection",
                    "fire_alert": "Fire Alert",
                }.get(cam.selected_model, cam.selected_model),
                "is_active": cam.is_active,
                "last_status": state.get("status") or cam.last_status or "Stopped",
                "last_error": state.get("error") or cam.last_error,
            }
        )

    counts = crud.get_latest_counts(db)
    summary = crud.get_ppe_summary(db)
    alerts = crud.get_latest_ppe_alerts(db)
    notifications = crud.get_all_notifications(db)
    violations = crud.get_latest_violations(db)
    violation_daily = crud.get_violation_daily(db)

    compliance_value = 0
    try:
        compliance_value = int(str(summary.get("compliance_rate", "0")).replace("%", ""))
    except Exception:
        compliance_value = 0

    return {
        "request": request,
        "active_page": active_page,
        "user_id": user.id,
        "username": user.name or "User",
        "today": datetime.now().strftime("%d %b %Y"),
        "time_window": datetime.now().strftime("%I:%M %p"),
        "model_options": MODEL_OPTIONS,
        "selected_page_model": "ppe",
        "counts": counts,
        "summary": summary,
        "alerts": alerts,
        "notifications": notifications,
        "violations": violations,
        "cameras": camera_cards,
        "compliance_value": compliance_value,
        "violation_chart_labels": list(violation_daily.keys()),
        "violation_chart_values": list(violation_daily.values()),
        "ppe_chart_labels": ["Hardhat", "Vest", "Mask", "Gloves"],
        "ppe_chart_values": [
            summary.get("hardhat", 0),
            summary.get("vest", 0),
            summary.get("mask", 0),
            summary.get("gloves", 0),
        ],
        "alert_pie_labels": ["Hardhat", "Vest", "Mask", "Gloves"],
        "alert_pie_values": [
            alerts.get("hardhat", {}).get("count", 0),
            alerts.get("vest", {}).get("count", 0),
            alerts.get("mask", {}).get("count", 0),
            alerts.get("gloves", {}).get("count", 0),
        ],
    }


@app.get("/login")
def login_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_email(db, email.strip())
    if not user or user.password != password:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password"},
            status_code=400,
        )

    request.session["user_id"] = user.id
    request.session["user_name"] = user.name or "User"
    return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)


@app.get("/signup")
def signup_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("signup.html", {"request": request, "error": None})


@app.post("/signup")
def signup(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = crud.get_user_by_email(db, email.strip())
    if existing:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "Email already registered"},
            status_code=400,
        )

    crud.create_user(
        db,
        schemas.UserCreate(
            name=name.strip(),
            email=email.strip(),
            password=password,
        ),
    )
    return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)


@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    context = build_common_context(request, db, "dashboard", user)
    return templates.TemplateResponse("dashboard.html", context)


@app.get("/camera-feed")
def camera_feed_page(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    context = build_common_context(request, db, "camera_feed", user)
    return templates.TemplateResponse("camera_feed.html", context)


@app.get("/notifications")
def notifications_page(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    context = build_common_context(request, db, "notifications", user)
    return templates.TemplateResponse("notifications.html", context)


@app.get("/reports")
def reports_page(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    context = build_common_context(request, db, "reports", user)
    return templates.TemplateResponse("reports.html", context)



@app.post("/remove-all-data")
def remove_all_data(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    user_cameras = crud.get_user_cameras(db, user.id)
    for cam in user_cameras:
        try:
            stop_camera_stream(cam.id)
        except Exception:
            pass

    db.query(models.FrameNotification).delete()
    db.query(models.FrameSummary).delete()
    db.query(models.PersonPPEStatus).delete()
    db.query(models.PPEAlertSummary).delete()

    for cam in user_cameras:
        db.delete(cam)

    db.commit()
    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)



@app.get("/add-camera")
def add_camera_page(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    context = build_common_context(request, db, "add_camera", user)
    return templates.TemplateResponse("camera.html", context)


@app.post("/add-camera")
def add_single_camera(
    request: Request,
    name: str = Form(...),
    source: str = Form(...),
    selected_model: str = Form("ppe"),
    db: Session = Depends(get_db),
):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    camera = crud.create_camera(
        db,
        schemas.CameraCreate(
            user_id=user.id,
            name=name.strip(),
            source=source.strip(),
            selected_model=selected_model.strip(),
        ),
    )

    start_camera_stream(
        camera.id,
        camera.user_id,
        camera.name,
        camera.source,
        camera.selected_model,
    )

    return RedirectResponse(url="/add-camera", status_code=HTTP_303_SEE_OTHER)


@app.post("/cameras/bulk-form")
def add_bulk_cameras(
    request: Request,
    camera_lines: str = Form(...),
    selected_model: str = Form("ppe"),
    db: Session = Depends(get_db),
):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    items = []

    for idx, raw_line in enumerate(camera_lines.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        if "|" in line:
            name, source = [part.strip() for part in line.split("|", 1)]
        elif "," in line:
            name, source = [part.strip() for part in line.split(",", 1)]
        else:
            name = f"Camera {idx}"
            source = line

        if source:
            items.append(
                schemas.CameraBatchItem(
                    name=name if name else f"Camera {idx}",
                    source=source,
                    selected_model=selected_model,
                )
            )

    created = crud.create_cameras_bulk(db, user_id=user.id, cameras=items)

    for cam in created:
        start_camera_stream(
            cam.id,
            cam.user_id,
            cam.name,
            cam.source,
            cam.selected_model,
        )

    return RedirectResponse(url="/add-camera", status_code=HTTP_303_SEE_OTHER)


@app.post("/cameras/{camera_id}/model")
def update_camera_model(
    request: Request,
    camera_id: int,
    selected_model: str = Form(...),
    db: Session = Depends(get_db),
):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    cam = crud.get_camera(db, camera_id)
    if not cam or cam.user_id != user.id:
        raise HTTPException(status_code=404, detail="Camera not found")

    crud.update_camera_model(db, camera_id, selected_model)

    updated = crud.get_camera(db, camera_id)
    if updated:
        stop_camera_stream(camera_id)

        import time
        time.sleep(0.2)

        start_camera_stream(
            updated.id,
            updated.user_id,
            updated.name,
            updated.source,
            updated.selected_model,
        )

    return RedirectResponse(url="/add-camera", status_code=HTTP_303_SEE_OTHER)


@app.post("/cameras/{camera_id}/start")
def start_camera(request: Request, camera_id: int, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    cam = crud.get_camera(db, camera_id)
    if not cam or cam.user_id != user.id:
        raise HTTPException(status_code=404, detail="Camera not found")

    start_camera_stream(
        cam.id,
        cam.user_id,
        cam.name,
        cam.source,
        cam.selected_model,
    )

    return RedirectResponse(url="/camera-feed", status_code=HTTP_303_SEE_OTHER)


@app.post("/cameras/{camera_id}/stop")
def stop_camera(request: Request, camera_id: int, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    cam = crud.get_camera(db, camera_id)
    if not cam or cam.user_id != user.id:
        raise HTTPException(status_code=404, detail="Camera not found")

    stop_camera_stream(camera_id)
    return RedirectResponse(url="/camera-feed", status_code=HTTP_303_SEE_OTHER)


@app.get("/users/{user_id}/cameras/", response_model=List[schemas.CameraOut])
def get_user_cameras(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return crud.get_user_cameras(db, user_id)


@app.get("/stream/{camera_id}")
def camera_stream(camera_id: int):
    def generate():
        import time

        while True:
            frame = get_latest_frame_bytes(camera_id)
            if frame is None:
                time.sleep(0.10)
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)