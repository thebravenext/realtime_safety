import cv2

from app.db.database import SessionLocal
from app.db from app.db import crud


def probe_source(source: str) -> tuple[bool, str]:
    src = int(source) if str(source).isdigit() else source
    cap = cv2.VideoCapture(src)
    ok = cap.isOpened()
    if ok:
        ok, _ = cap.read()
    cap.release()
    return ok, "OK" if ok else "Failed"


def main():
    db = SessionLocal()
    try:
        cameras = crud.get_all_cameras(db)
        if not cameras:
            print("No cameras found.")
            return

        for camera in cameras:
            ok, message = probe_source(camera.source)
            print(
                f"Camera {camera.id} | {camera.name} | {camera.source} | "
                f"Model: {camera.selected_model} -> {message}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()