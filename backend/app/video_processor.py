from pathlib import Path

import cv2
from ultralytics import YOLO


from typing import Optional, Callable, Any

# Project root:
# D:/Projects/CCTV surveillance/
BASE_DIR = Path(__file__).resolve().parents[2]

VIDEO_PATH = BASE_DIR / "storage" / "videos" / "sample.mp4"
OUTPUT_DIR = BASE_DIR / "storage" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# YOLO model
MODEL_PATH = BASE_DIR / "yolov8n.pt"


def process_video(
    video_path: str | Path = VIDEO_PATH,
    output_filename: str = "bytetrack_detected.mp4",
    init_callback: Optional[Callable[[int, int, float], None]] = None,
    frame_callback: Optional[Callable[[Any, float, list], None]] = None,
    progress_callback: Optional[Callable[[int, int, int], None]] = None
) -> str:
    video_path = Path(video_path)

    print("=" * 60)
    print("AURA SURVEILLANCE - YOLO + BYTETRACK")
    print("=" * 60)

    print(f"Video: {video_path}")
    print(f"Model: {MODEL_PATH}")

    if not video_path.exists():
        print("ERROR: Video file not found.")
        return

    if not MODEL_PATH.exists():
        print("ERROR: YOLO model not found.")
        return

    # ---------------------------------------------------------
    # LOAD YOLO
    # ---------------------------------------------------------

    print("Loading YOLO model...")

    model = YOLO(str(MODEL_PATH))

    print("YOLO model loaded successfully.")
    print("ByteTrack tracker: READY")
    print("-" * 60)

    # ---------------------------------------------------------
    # OPEN VIDEO
    # ---------------------------------------------------------

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print("ERROR: Could not open video.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    duration = frame_count / fps if fps > 0 else 0

    print(f"FPS: {fps:.2f}")
    print(f"Resolution: {width} x {height}")
    print(f"Total Frames: {frame_count}")
    print(f"Duration: {duration:.2f} seconds")
    print("-" * 60)

    if init_callback:
        init_callback(width, height, fps)

    # ---------------------------------------------------------
    # OUTPUT VIDEO
    # ---------------------------------------------------------

    output_path = OUTPUT_DIR / output_filename
    
    if output_filename.endswith(".webm"):
        fourcc = cv2.VideoWriter_fourcc(*"vp80")
    else:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    writer = cv2.VideoWriter(
        str(output_path),
        fourcc,
        fps,
        (width, height)
    )

    if not writer.isOpened():
        print("ERROR: Could not create output video.")
        cap.release()
        return

    # ---------------------------------------------------------
    # PROCESS
    # ---------------------------------------------------------

    processed_frames = 0
    total_detections = 0

    unique_track_ids = set()

    while True:

        success, frame = cap.read()

        if not success:
            break

        processed_frames += 1

        # -----------------------------------------------------
        # YOLO + BYTETRACK
        # -----------------------------------------------------

        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],       # 0 = person
            conf=0.35,
            verbose=False
        )

        result = results[0]

        # Start with original frame
        annotated_frame = frame.copy()

        boxes = result.boxes

        if boxes is not None and len(boxes) > 0:

            xyxy = boxes.xyxy.cpu().numpy()
            confidences = boxes.conf.cpu().numpy()
            classes = boxes.cls.cpu().numpy()

            # Track IDs may not exist on the first few frames
            if boxes.id is not None:
                track_ids = boxes.id.cpu().numpy().astype(int)
            else:
                track_ids = [-1] * len(boxes)

            for box, confidence, class_id, track_id in zip(
                xyxy,
                confidences,
                classes,
                track_ids
            ):

                x1, y1, x2, y2 = map(int, box)

                class_id = int(class_id)
                track_id = int(track_id)

                # Only person detections
                if class_id != 0:
                    continue

                total_detections += 1

                if track_id >= 0:
                    unique_track_ids.add(track_id)

                # -------------------------------------------------
                # DRAW BOUNDING BOX
                # -------------------------------------------------

                cv2.rectangle(
                    annotated_frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                # -------------------------------------------------
                # LABEL
                # -------------------------------------------------

                if track_id >= 0:
                    label = f"Person ID {track_id} | {confidence:.2f}"
                else:
                    label = f"Person | {confidence:.2f}"

                # Label background
                (text_width, text_height), baseline = cv2.getTextSize(
                    label,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    2
                )

                cv2.rectangle(
                    annotated_frame,
                    (x1, max(0, y1 - text_height - baseline - 8)),
                    (
                        x1 + text_width + 8,
                        y1
                    ),
                    (0, 255, 0),
                    -1
                )

                # Label text
                cv2.putText(
                    annotated_frame,
                    label,
                    (x1 + 4, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),
                    2,
                    cv2.LINE_AA
                )
                
        if frame_callback:
            # Prepare detection data for the pipeline
            detections_data = []
            if boxes is not None and len(boxes) > 0:
                for box, confidence, class_id, track_id in zip(xyxy, confidences, classes, track_ids):
                    detections_data.append({
                        "x1": box[0], "y1": box[1], "x2": box[2], "y2": box[3],
                        "confidence": confidence,
                        "class_id": class_id,
                        "track_id": track_id
                    })
            
            # Use simulated time base (start of 2026-08-28 09:00:00 or current real time + offset)
            # To allow chronological evaluation in the rule engine, we map frame count to time
            # 9:00 AM local time simulated
            import time
            simulated_timestamp = time.time() + (processed_frames / fps) if fps > 0 else time.time()
            frame_callback(annotated_frame, simulated_timestamp, detections_data)

        # ---------------------------------------------------------
        # SAVE FIRST TRACKED FRAME
        # ---------------------------------------------------------

        if processed_frames == 1:

            first_frame_path = (
                OUTPUT_DIR / "bytetrack_first_frame.jpg"
            )

            cv2.imwrite(
                str(first_frame_path),
                annotated_frame
            )

            print("First ByteTrack frame saved:")
            print(first_frame_path)

        # ---------------------------------------------------------
        # WRITE VIDEO
        # ---------------------------------------------------------

        writer.write(annotated_frame)

        # ---------------------------------------------------------
        # PROGRESS
        # ---------------------------------------------------------

        if processed_frames % 100 == 0:
            print(
                f"Processed frames: {processed_frames}/{frame_count} | "
                f"Detections: {total_detections} | "
                f"Unique Track IDs: {len(unique_track_ids)}"
            )
            
        if progress_callback and processed_frames % 10 == 0:
            progress_callback(processed_frames, frame_count, total_detections)

    # ---------------------------------------------------------
    # CLEANUP
    # ---------------------------------------------------------

    cap.release()
    writer.release()

    print("-" * 60)
    print("YOLO + ByteTrack processing completed.")
    print(f"Frames processed: {processed_frames}")
    print(f"Person detections: {total_detections}")
    print(f"Unique Track IDs: {len(unique_track_ids)}")
    print(f"Output video: {output_path}")
    print("=" * 60)
    
    # Fire final progress callback
    if progress_callback:
        progress_callback(processed_frames, frame_count, total_detections)
        
    return str(output_path)


if __name__ == "__main__":
    process_video()