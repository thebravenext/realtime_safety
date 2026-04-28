import os
import threading
import time
from collections import Counter
from typing import Any

import cv2
from ultralytics import YOLO

from app.db from app.db import crud
from app.db.database import SessionLocal

PPE_MODEL_PATH = os.getenv("PPE_MODEL_PATH", "data/models/PPE_Model.pt")
TRUCK_MODEL_PATH = os.getenv("TRUCK_MODEL_PATH", "data/models/PPE_Model.pt")
FIRE_MODEL_PATH = os.getenv("FIRE_MODEL_PATH", "data/models/a.pt")

PROCESS_EVERY_N_FRAMES = int(os.getenv("PROCESS_EVERY_N_FRAMES", "3"))
TARGET_PROCESS_FPS = float(os.getenv("TARGET_PROCESS_FPS", "4"))
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", "960"))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", "540"))
SNAPSHOT_INTERVAL_SEC = float(os.getenv("SNAPSHOT_INTERVAL_SEC", "4"))
SUMMARY_INTERVAL_SEC = float(os.getenv("SUMMARY_INTERVAL_SEC", "1.0"))
PERSON_SAVE_EVERY_N = int(os.getenv("PERSON_SAVE_EVERY_N", "5"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "80"))

os.makedirs("app/static/violations", exist_ok=True)

MODEL_CACHE: dict[str, YOLO] = {}
MODEL_INIT_LOCK = threading.Lock()
MODEL_INFER_LOCK = threading.Lock()

STREAMS: dict[int, dict[str, Any]] = {}
STREAMS_LOCK = threading.Lock()

LATEST_FRAMES: dict[int, bytes] = {}
LATEST_FRAMES_LOCK = threading.Lock()


def _model_path_for(mode: str) -> str:
    if mode == "truck_inspection":
        return TRUCK_MODEL_PATH
    if mode == "fire_alert":
        return FIRE_MODEL_PATH
    return PPE_MODEL_PATH


def _get_model(mode: str) -> YOLO:
    path = _model_path_for(mode)

    if not os.path.exists(path):
        if mode != "ppe" and os.path.exists(PPE_MODEL_PATH):
            path = PPE_MODEL_PATH
        else:
            raise FileNotFoundError(f"Model file not found: {path}")

    with MODEL_INIT_LOCK:
        if path not in MODEL_CACHE:
            MODEL_CACHE[path] = YOLO(path)
        return MODEL_CACHE[path]


def _update_stream_state(cam_id: int, **kwargs):
    with STREAMS_LOCK:
        if cam_id not in STREAMS:
            return
        STREAMS[cam_id].update(kwargs)


def _set_latest_frame(cam_id: int, frame) -> None:
    ok, buffer = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
    )
    if ok:
        with LATEST_FRAMES_LOCK:
            LATEST_FRAMES[cam_id] = buffer.tobytes()


def get_latest_frame_bytes(cam_id: int) -> bytes | None:
    with LATEST_FRAMES_LOCK:
        return LATEST_FRAMES.get(cam_id)


def get_stream_statuses() -> dict[int, dict[str, Any]]:
    with STREAMS_LOCK:
        return {
            cam_id: {
                "running": info["thread"].is_alive() and not info["stop_event"].is_set(),
                "status": info.get("status", "Stopped"),
                "error": info.get("error"),
                "selected_model": info.get("selected_model", "ppe"),
            }
            for cam_id, info in STREAMS.items()
        }


def _open_capture(source: str):
    src = int(source) if str(source).isdigit() else source
    cap = cv2.VideoCapture(src)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def _save_violation_image(frame, cam_id: int, frame_index: int) -> str:
    filename = f"camera_{cam_id}_frame_{frame_index}.jpg"
    full_path = os.path.join("app", "static", "violations", filename)
    cv2.imwrite(full_path, frame)
    return f"/static/violations/{filename}"


def _calculate_drop(missing: int, safe: int) -> float:
    total = missing + safe
    return round((missing / total) * 100.0, 2) if total else 0.0


def _normalize_label(label: str) -> str:
    text = label.strip().lower()

    if "person" in text:
        return "person"

    is_missing = any(token in text for token in ["no", "without", "missing"])

    if "hardhat" in text or "helmet" in text:
        return "hardhat_missing" if is_missing else "hardhat"
    if "glove" in text:
        return "gloves_missing" if is_missing else "gloves"
    if "mask" in text:
        return "mask_missing" if is_missing else "mask"
    if "vest" in text or "jacket" in text:
        return "vest_missing" if is_missing else "vest"

    if "truck" in text or "lorry" in text:
        if "empty" in text:
            return "empty_truck"
        if "full" in text or "loaded" in text:
            return "full_truck"
        return "truck"

    if "plate" in text or "numberplate" in text or "license" in text:
        return "plate"

    if "fire" in text:
        return "fire"
    if "smoke" in text:
        return "smoke"

    return text


def _draw_boxes(frame, result, names):
    if result.boxes is None:
        return

    for box, cls in zip(result.boxes.xyxy.tolist(), result.boxes.cls.tolist()):
        x1, y1, x2, y2 = [int(v) for v in box]
        label = names[int(cls)]
        label_low = label.lower()

        if any(k in label_low for k in ["no", "missing", "fire", "smoke", "empty"]):
            color = (0, 0, 255)
        elif "truck" in label_low:
            color = (0, 165, 255)
        else:
            color = (0, 200, 0)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            label,
            (x1, max(y1 - 8, 16)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )


def _build_ppe_rows(user_id: int, cam_id: int, frame_index: int, normalized_labels: list[str]):
    counts = Counter(normalized_labels)
    num_persons = counts.get("person", 0)
    persons = []

    for idx in range(num_persons):
        persons.append(
            {
                "user_id": user_id,
                "camera_id": cam_id,
                "frame_index": frame_index,
                "person_id": idx + 1,
                "person": "detected",
                "gloves": "missing",
                "hardhat": "missing",
                "mask": "missing",
                "vest": "missing",
            }
        )

    for idx in range(min(num_persons, counts.get("gloves", 0))):
        persons[idx]["gloves"] = "wearing"
    for idx in range(min(num_persons, counts.get("hardhat", 0))):
        persons[idx]["hardhat"] = "wearing"
    for idx in range(min(num_persons, counts.get("mask", 0))):
        persons[idx]["mask"] = "wearing"
    for idx in range(min(num_persons, counts.get("vest", 0))):
        persons[idx]["vest"] = "wearing"

    return persons, counts


def _ocr_number_plate_placeholder(frame) -> str:
    return ""


def _process_ppe_mode(user_id, cam_id, frame_index, frame, result, names):
    labels = [names[int(cls)] for cls in result.boxes.cls.tolist()] if result.boxes is not None else []
    normalized = [_normalize_label(label) for label in labels]

    person_rows, counts = _build_ppe_rows(user_id, cam_id, frame_index, normalized)

    wearing = sum(
        1
        for person in person_rows
        for key in ["gloves", "hardhat", "mask", "vest"]
        if person[key] == "wearing"
    )
    not_wearing = max((len(person_rows) * 4) - wearing, 0)
    persons = len(person_rows)

    image_url = _save_violation_image(frame, cam_id, frame_index) if not_wearing > 0 else None

    notifications = []
    if image_url:
        for person in person_rows:
            for item in ["gloves", "hardhat", "mask", "vest"]:
                if person[item] == "missing":
                    notifications.append(
                        {
                            "user_id": user_id,
                            "camera_id": cam_id,
                            "frame_index": frame_index,
                            "person_id": person["person_id"],
                            "violation_type": f"NO-{item.upper()}",
                            "message": f"Camera {cam_id}: Person {person['person_id']} missing {item}",
                            "image_url": image_url,
                        }
                    )

    alert_row = {
        "user_id": user_id,
        "camera_id": cam_id,
        "hardhat_count": counts.get("hardhat_missing", 0),
        "hardhat_drop": _calculate_drop(counts.get("hardhat_missing", 0), counts.get("hardhat", 0)),
        "vest_count": counts.get("vest_missing", 0),
        "vest_drop": _calculate_drop(counts.get("vest_missing", 0), counts.get("vest", 0)),
        "mask_count": counts.get("mask_missing", 0),
        "mask_drop": _calculate_drop(counts.get("mask_missing", 0), counts.get("mask", 0)),
        "gloves_count": counts.get("gloves_missing", 0),
        "gloves_drop": _calculate_drop(counts.get("gloves_missing", 0), counts.get("gloves", 0)),
    }

    frame_summary = {
        "user_id": user_id,
        "camera_id": cam_id,
        "frame_index": frame_index,
        "wearing": wearing,
        "not_wearing": not_wearing,
        "persons": persons,
        "in_count": persons,
        "out_count": 0,
        "inference_ms": 0.0,
    }

    return frame_summary, person_rows, notifications, alert_row, persons


def _simple_truck_fill_state(frame, box) -> str:
    x1, y1, x2, y2 = [max(0, int(v)) for v in box]
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return "unknown"

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    return "empty" if brightness > 120 else "full"


def _process_truck_mode(user_id, cam_id, frame_index, frame, result, names):
    labels = [names[int(cls)] for cls in result.boxes.cls.tolist()] if result.boxes is not None else []
    normalized = [_normalize_label(label) for label in labels]
    counts = Counter(normalized)

    people_count = counts.get("person", 0)
    truck_count = counts.get("truck", 0) + counts.get("empty_truck", 0) + counts.get("full_truck", 0)

    notifications = []
    image_url = None
    empty_count = 0
    full_count = 0

    if result.boxes is not None:
        for box, cls in zip(result.boxes.xyxy.tolist(), result.boxes.cls.tolist()):
            label = names[int(cls)]
            norm = _normalize_label(label)
            if norm in {"truck", "empty_truck", "full_truck"}:
                fill_state = _simple_truck_fill_state(frame, box)
                if fill_state == "empty":
                    empty_count += 1
                elif fill_state == "full":
                    full_count += 1

    plate_text = _ocr_number_plate_placeholder(frame)

    if empty_count > 0:
        image_url = _save_violation_image(frame, cam_id, frame_index)
        notifications.append(
            {
                "user_id": user_id,
                "camera_id": cam_id,
                "frame_index": frame_index,
                "person_id": 0,
                "violation_type": "EMPTY-TRUCK-ALERT",
                "message": f"Camera {cam_id}: Empty truck detected",
                "image_url": image_url,
            }
        )

    if plate_text:
        notifications.append(
            {
                "user_id": user_id,
                "camera_id": cam_id,
                "frame_index": frame_index,
                "person_id": 0,
                "violation_type": "NUMBER-PLATE",
                "message": f"Camera {cam_id}: Number plate {plate_text}",
                "image_url": image_url,
            }
        )

    frame_summary = {
        "user_id": user_id,
        "camera_id": cam_id,
        "frame_index": frame_index,
        "wearing": 0,
        "not_wearing": 0,
        "persons": people_count,
        "in_count": truck_count,
        "out_count": 0,
        "inference_ms": 0.0,
    }

    cv2.putText(
        frame,
        f"Trucks:{truck_count} Empty:{empty_count} Full:{full_count} People:{people_count}",
        (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )

    return frame_summary, [], notifications, None, people_count


def _process_fire_mode(user_id, cam_id, frame_index, frame, result, names):
    labels = [names[int(cls)] for cls in result.boxes.cls.tolist()] if result.boxes is not None else []
    normalized = [_normalize_label(label) for label in labels]
    counts = Counter(normalized)

    people_count = counts.get("person", 0)
    fire_count = counts.get("fire", 0)
    smoke_count = counts.get("smoke", 0)

    notifications = []
    image_url = None

    if fire_count > 0 or smoke_count > 0:
        image_url = _save_violation_image(frame, cam_id, frame_index)
        if fire_count > 0:
            notifications.append(
                {
                    "user_id": user_id,
                    "camera_id": cam_id,
                    "frame_index": frame_index,
                    "person_id": 0,
                    "violation_type": "FIRE-ALERT",
                    "message": f"Camera {cam_id}: Fire detected",
                    "image_url": image_url,
                }
            )
        if smoke_count > 0:
            notifications.append(
                {
                    "user_id": user_id,
                    "camera_id": cam_id,
                    "frame_index": frame_index,
                    "person_id": 0,
                    "violation_type": "SMOKE-ALERT",
                    "message": f"Camera {cam_id}: Smoke detected",
                    "image_url": image_url,
                }
            )

    frame_summary = {
        "user_id": user_id,
        "camera_id": cam_id,
        "frame_index": frame_index,
        "wearing": 0,
        "not_wearing": 0,
        "persons": people_count,
        "in_count": people_count,
        "out_count": 0,
        "inference_ms": 0.0,
    }

    cv2.putText(
        frame,
        f"Fire:{fire_count} Smoke:{smoke_count} People:{people_count}",
        (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )

    return frame_summary, [], notifications, None, people_count


def _camera_loop(cam_id: int, user_id: int, name: str, source: str, selected_model: str, stop_event: threading.Event):
    db = SessionLocal()
    cap = None

    try:
        crud.update_camera_runtime(db, cam_id, is_active=True, last_status="Connecting", last_error=None)
        _update_stream_state(cam_id, status="Connecting", error=None, selected_model=selected_model)

        cap = _open_capture(source)
        if not cap.isOpened():
            message = f"Cannot open source: {source}"
            crud.update_camera_runtime(db, cam_id, is_active=False, last_status="Error", last_error=message)
            _update_stream_state(cam_id, status="Error", error=message, selected_model=selected_model)
            return

        model = _get_model(selected_model)
        crud.update_camera_runtime(db, cam_id, is_active=True, last_status="Running", last_error=None)
        _update_stream_state(cam_id, status="Running", error=None, selected_model=selected_model)

        raw_index = 0
        processed_index = 0
        last_process_time = 0.0
        min_interval = 1.0 / max(TARGET_PROCESS_FPS, 0.1)

        while not stop_event.is_set():
            camera = crud.get_camera(db, cam_id)
            current_mode = camera.selected_model if camera and camera.selected_model else selected_model
            if current_mode != selected_model:
                selected_model = current_mode
                model = _get_model(selected_model)

            ret, frame = cap.read()
            if not ret:
                if isinstance(source, str) and os.path.isfile(source):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                crud.update_camera_runtime(db, cam_id, is_active=True, last_status="Reconnecting", last_error=None)
                _update_stream_state(cam_id, status="Reconnecting", error=None, selected_model=selected_model)
                if cap is not None:
                    cap.release()
                time.sleep(1.5)
                cap = _open_capture(source)
                continue

            raw_index += 1
            now = time.monotonic()
            if raw_index % PROCESS_EVERY_N_FRAMES != 0:
                continue
            if now - last_process_time < min_interval:
                continue

            last_process_time = now
            processed_index += 1

            if FRAME_WIDTH > 0 and FRAME_HEIGHT > 0:
                frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            t0 = time.perf_counter()
            with MODEL_INFER_LOCK:
                result = model(frame, verbose=False)[0]
            inference_ms = round((time.perf_counter() - t0) * 1000.0, 2)

            _draw_boxes(frame, result, model.names)

            cv2.putText(
                frame,
                f"{name} | Model: {selected_model} | {inference_ms} ms",
                (10, FRAME_HEIGHT - 12 if FRAME_HEIGHT > 0 else 520),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

            if selected_model == "truck_inspection":
                frame_summary, person_rows, notifications, alert_row, persons = _process_truck_mode(
                    user_id, cam_id, processed_index, frame, result, model.names
                )
            elif selected_model == "fire_alert":
                frame_summary, person_rows, notifications, alert_row, persons = _process_fire_mode(
                    user_id, cam_id, processed_index, frame, result, model.names
                )
            else:
                frame_summary, person_rows, notifications, alert_row, persons = _process_ppe_mode(
                    user_id, cam_id, processed_index, frame, result, model.names
                )

            frame_summary["inference_ms"] = inference_ms

            if selected_model in ["truck_inspection", "fire_alert"]:
                cv2.putText(
                    frame,
                    f"Persons: {persons}",
                    (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

            _set_latest_frame(cam_id, frame)

            crud.save_detection_cycle(
                db,
                frame_summary=frame_summary,
                person_rows=person_rows if selected_model == "ppe" and processed_index % PERSON_SAVE_EVERY_N == 0 else [],
                notification_rows=notifications,
                alert_row=alert_row,
            )

            crud.update_camera_runtime(
                db,
                cam_id,
                is_active=True,
                last_status=f"Running ({selected_model})",
                last_error=None,
            )
            _update_stream_state(
                cam_id,
                status=f"Running ({selected_model})",
                error=None,
                selected_model=selected_model,
            )

        crud.update_camera_runtime(db, cam_id, is_active=False, last_status="Stopped", last_error=None)
        _update_stream_state(cam_id, status="Stopped", error=None, selected_model=selected_model)

    except Exception as exc:
        message = str(exc)
        crud.update_camera_runtime(db, cam_id, is_active=False, last_status="Error", last_error=message)
        _update_stream_state(cam_id, status="Error", error=message, selected_model=selected_model)
    finally:
        if cap is not None:
            cap.release()
        db.close()


def start_camera_stream(cam_id: int, user_id: int, name: str, source: str, selected_model: str) -> bool:
    with STREAMS_LOCK:
        existing = STREAMS.get(cam_id)
        if existing and existing["thread"].is_alive() and not existing["stop_event"].is_set():
            return False

        stop_event = threading.Event()
        thread = threading.Thread(
            target=_camera_loop,
            args=(cam_id, user_id, name, source, selected_model, stop_event),
            daemon=True,
            name=f"camera-{cam_id}",
        )
        STREAMS[cam_id] = {
            "thread": thread,
            "stop_event": stop_event,
            "status": "Starting",
            "error": None,
            "selected_model": selected_model,
        }
        thread.start()
        return True


def stop_camera_stream(cam_id: int) -> bool:
    with STREAMS_LOCK:
        info = STREAMS.get(cam_id)
        if not info:
            return False
        info["stop_event"].set()
        info["status"] = "Stopping"
        return True


def start_all_camera_streams() -> None:
    db = SessionLocal()
    try:
        crud.ensure_default_user(db)
        cameras = crud.get_all_cameras(db)
        for cam in cameras:
            start_camera_stream(cam.id, cam.user_id, cam.name, cam.source, cam.selected_model)
    finally:
        db.close()