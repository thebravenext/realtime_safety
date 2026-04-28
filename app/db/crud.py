from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas


def ensure_default_user(db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.email == "admin@example.com").first()
    if user:
        return user

    user = models.User(
        name="Admin",
        email="admin@example.com",
        password="admin123",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    user_obj = models.User(
        name=user.name,
        email=user.email,
        password=user.password,
    )
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj


def create_camera(db: Session, camera: schemas.CameraCreate) -> models.Camera:
    existing = db.query(models.Camera).filter(
        models.Camera.user_id == camera.user_id,
        models.Camera.source == camera.source,
    ).first()
    if existing:
        return existing

    cam = models.Camera(
        user_id=camera.user_id,
        name=camera.name.strip(),
        source=camera.source.strip(),
        selected_model=(camera.selected_model or "ppe").strip(),
        is_active=False,
        last_status="Stopped",
    )
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return cam


def create_cameras_bulk(db: Session, user_id: int, cameras: list[schemas.CameraBatchItem]) -> list[models.Camera]:
    created: list[models.Camera] = []
    seen_sources: set[str] = set()

    for item in cameras:
        source = item.source.strip()
        name = item.name.strip() or "Camera"
        selected_model = (item.selected_model or "ppe").strip()

        if not source or source in seen_sources:
            continue
        seen_sources.add(source)

        existing = db.query(models.Camera).filter(
            models.Camera.user_id == user_id,
            models.Camera.source == source,
        ).first()
        if existing:
            created.append(existing)
            continue

        cam = models.Camera(
            user_id=user_id,
            name=name,
            source=source,
            selected_model=selected_model,
            is_active=False,
            last_status="Stopped",
        )
        db.add(cam)
        db.flush()
        created.append(cam)

    db.commit()
    for cam in created:
        db.refresh(cam)
    return created


def get_user_cameras(db: Session, user_id: int) -> list[models.Camera]:
    return (
        db.query(models.Camera)
        .filter(models.Camera.user_id == user_id)
        .order_by(models.Camera.id.asc())
        .all()
    )


def get_all_cameras(db: Session) -> list[models.Camera]:
    return db.query(models.Camera).order_by(models.Camera.id.asc()).all()


def get_camera(db: Session, camera_id: int) -> models.Camera | None:
    return db.query(models.Camera).filter(models.Camera.id == camera_id).first()


def update_camera_model(db: Session, camera_id: int, selected_model: str):
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        return None
    cam.selected_model = selected_model
    db.commit()
    db.refresh(cam)
    return cam


def update_camera_runtime(
    db: Session,
    camera_id: int,
    *,
    is_active: bool,
    last_status: str,
    last_error: str | None = None,
) -> None:
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        return
    cam.is_active = is_active
    cam.last_status = last_status
    cam.last_error = last_error
    db.commit()


def save_detection_cycle(
    db: Session,
    *,
    frame_summary: dict | None,
    person_rows: list[dict] | None = None,
    notification_rows: list[dict] | None = None,
    alert_row: dict | None = None,
) -> None:
    if frame_summary:
        db.add(models.FrameSummary(**frame_summary))

    for row in person_rows or []:
        db.add(models.PersonPPEStatus(**row))

    for row in notification_rows or []:
        db.add(models.FrameNotification(**row))

    if alert_row:
        db.add(models.PPEAlertSummary(**alert_row))

    db.commit()


def get_latest_counts(db: Session) -> dict:
    cameras = get_all_cameras(db)
    total_in = 0
    total_out = 0

    for cam in cameras:
        row = (
            db.query(models.FrameSummary)
            .filter(models.FrameSummary.camera_id == cam.id)
            .order_by(models.FrameSummary.timestamp.desc())
            .first()
        )
        if row:
            total_in += row.in_count
            total_out += row.out_count

    total_inside = max(total_in - total_out, 0)
    return {"in_": total_in, "out": total_out, "total_inside": total_inside}


def get_ppe_summary(db: Session) -> dict:
    rows = (
        db.query(models.PersonPPEStatus)
        .order_by(models.PersonPPEStatus.timestamp.desc())
        .limit(300)
        .all()
    )

    if not rows:
        return {
            "hardhat": 0,
            "mask": 0,
            "gloves": 0,
            "vest": 0,
            "wearing": 0,
            "not_wearing": 0,
            "compliance_rate": "0%",
        }

    total_people = len(rows)
    wearing_counts = {
        "hardhat": sum(1 for r in rows if r.hardhat == "wearing"),
        "mask": sum(1 for r in rows if r.mask == "wearing"),
        "gloves": sum(1 for r in rows if r.gloves == "wearing"),
        "vest": sum(1 for r in rows if r.vest == "wearing"),
    }

    total_items = total_people * 4
    total_wearing = sum(wearing_counts.values())
    total_not_wearing = total_items - total_wearing
    compliance = int((total_wearing / total_items) * 100) if total_items else 0

    return {
        "hardhat": int((wearing_counts["hardhat"] / total_people) * 100),
        "mask": int((wearing_counts["mask"] / total_people) * 100),
        "gloves": int((wearing_counts["gloves"] / total_people) * 100),
        "vest": int((wearing_counts["vest"] / total_people) * 100),
        "wearing": total_wearing,
        "not_wearing": total_not_wearing,
        "compliance_rate": f"{compliance}%",
    }


def get_all_notifications(db: Session, limit: int = 50):
    rows = (
        db.query(models.FrameNotification)
        .order_by(models.FrameNotification.timestamp.desc())
        .limit(limit)
        .all()
    )

    return [
        schemas.FrameNotificationOut(
            frame_index=row.frame_index,
            person_id=row.person_id,
            violation_type=row.violation_type,
            message=row.message,
            timestamp=str(row.timestamp),
            camera_id=row.camera_id,
            image_url=row.image_url,
        )
        for row in rows
    ]


def get_latest_violations(db: Session, limit: int = 10):
    rows = (
        db.query(models.FrameNotification)
        .filter(models.FrameNotification.image_url.isnot(None))
        .order_by(models.FrameNotification.timestamp.desc())
        .limit(limit * 4)
        .all()
    )

    grouped = {}
    for row in rows:
        if not row.image_url:
            continue

        if row.image_url not in grouped:
            grouped[row.image_url] = {
                "image_url": row.image_url,
                "gate": f"Camera {row.camera_id}",
                "issues": [],
            }

        grouped[row.image_url]["issues"].append(row.violation_type)

        if len(grouped) >= limit:
            break

    return list(grouped.values())


def get_latest_ppe_alerts(db: Session) -> dict:
    cameras = get_all_cameras(db)

    total = {
        "hardhat": {"count": 0, "drop": 0.0},
        "vest": {"count": 0, "drop": 0.0},
        "mask": {"count": 0, "drop": 0.0},
        "gloves": {"count": 0, "drop": 0.0},
    }
    cameras_with_data = 0

    for cam in cameras:
        row = (
            db.query(models.PPEAlertSummary)
            .filter(models.PPEAlertSummary.camera_id == cam.id)
            .order_by(models.PPEAlertSummary.timestamp.desc())
            .first()
        )
        if not row:
            continue

        cameras_with_data += 1
        total["hardhat"]["count"] += row.hardhat_count
        total["vest"]["count"] += row.vest_count
        total["mask"]["count"] += row.mask_count
        total["gloves"]["count"] += row.gloves_count
        total["hardhat"]["drop"] += row.hardhat_drop
        total["vest"]["drop"] += row.vest_drop
        total["mask"]["drop"] += row.mask_drop
        total["gloves"]["drop"] += row.gloves_drop

    if cameras_with_data:
        for key in total:
            total[key]["drop"] = round(total[key]["drop"] / cameras_with_data, 2)

    return total


def get_violation_daily(db: Session, days: int = 7) -> dict[str, int]:
    start = datetime.utcnow() - timedelta(days=days - 1)

    rows = (
        db.query(models.FrameNotification)
        .filter(models.FrameNotification.timestamp >= start)
        .all()
    )

    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.timestamp is None:
            continue
        key = row.timestamp.strftime("%Y-%m-%d")
        counts[key] += 1

    ordered = {}
    for i in range(days):
        day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        ordered[day] = counts.get(day, 0)

    return ordered