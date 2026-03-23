"""Video processing: sample frames and detect trends over time."""

import cv2
import os
from typing import Dict, List
from .image_analyzer import analyze_image


def analyze_video(path: str, sample_rate: int = 5) -> Dict:
    """Analyze a video file by sampling one frame every `sample_rate` seconds.
    Returns aggregated detections and a simple trend analysis.
    """
    if not os.path.exists(path):
        raise ValueError(f"Video not found: {path}")

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError("Unable to open video file")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_sec = frame_count / fps if fps > 0 else 0

    interval_frames = max(1, int(fps * sample_rate))

    index = 0
    results: List[Dict] = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if index % interval_frames == 0:
            # Save a temporary frame to disk and analyze
            tmp_path = f"/tmp/plant_health_frame_{index}.jpg"
            cv2.imencode('.jpg', frame)[1].tofile(tmp_path)
            r = analyze_image(tmp_path, save_annotated=False)
            r['frame_index'] = index
            results.append(r)
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        index += 1

    cap.release()

    # Simple trend: compute green_ratio over time
    ratios = [r.get('green_ratio', 0.0) for r in results]
    trend = 'stable'
    if len(ratios) >= 3:
        # linear slope simple
        import numpy as np
        x = np.arange(len(ratios))
        slope = np.polyfit(x, ratios, 1)[0]
        if slope < -0.005:
            trend = 'declining_green'
        elif slope > 0.005:
            trend = 'improving_green'

    # Aggregate spot counts
    total_spots = sum(r.get('spot_count', 0) for r in results)

    return {
        'frames_analyzed': len(results),
        'duration_sec': duration_sec,
        'avg_green_ratio': round(float(sum(ratios) / max(1, len(ratios))), 3) if results else 0.0,
        'trend': trend,
        'total_spots': int(total_spots),
        'frame_results': results
    }
