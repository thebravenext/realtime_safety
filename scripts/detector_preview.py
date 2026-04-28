import argparse
import os

import cv2
from ultralytics import YOLO

MODEL_PATH = os.getenv("PPE_MODEL_PATH", "data/models/PPE_Model.pt")


def main():
    parser = argparse.ArgumentParser(description="Quick detector preview")
    parser.add_argument("--source", default="0", help="Camera index, video path, RTSP, or HTTP stream")
    parser.add_argument("--model", default=MODEL_PATH, help="YOLO model path")
    args = parser.parse_args()

    model = YOLO(args.model)
    source = int(args.source) if str(args.source).isdigit() else args.source
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"Cannot open source: {args.source}")
        return

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        results = model(frame, verbose=False)[0]
        if results.boxes is not None:
            for box, cls in zip(results.boxes.xyxy.tolist(), results.boxes.cls.tolist()):
                x1, y1, x2, y2 = [int(v) for v in box]
                label = model.names[int(cls)]
                color = (0, 0, 255) if "no" in label.lower() or "missing" in label.lower() else (0, 200, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, max(y1 - 8, 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("Detector Preview", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()