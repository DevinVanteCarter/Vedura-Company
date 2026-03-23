"""Simple image analysis heuristics for plant health detection.
Detects: yellowing (nutrient deficiency/burn), brown edges (burn),
spots/mold/pests, and light stress (over/under exposure).
"""

import cv2
import numpy as np
from typing import Dict, Tuple


def _load_image(path: str):
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Unable to load image: {path}")
    return img


def analyze_image(path: str, save_annotated: bool = True) -> Dict:
    img = _load_image(path)
    h, w = img.shape[:2]

    # Convert to different color spaces
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Basic stats
    mean_bgr = cv2.mean(img)[:3]
    mean_hsv = cv2.mean(hsv)[:3]
    mean_lab = cv2.mean(lab)[:3]

    findings = {}

    # Heuristic: yellowing detection -> lower green channel relative to red/blue
    b, g, r = mean_bgr
    green_ratio = g / max((r + b) / 2.0, 1e-6)
    findings['green_ratio'] = round(float(green_ratio), 3)
    if green_ratio < 0.85:
        findings['yellowing_suspected'] = True
        findings['yellowing_confidence'] = round(min(0.95, (0.85 - green_ratio) * 2.0), 2)
    else:
        findings['yellowing_suspected'] = False
        findings['yellowing_confidence'] = 0.0

    # Heuristic: brown / burnt edges via edge detection combined with brown color threshold
    edges = cv2.Canny(gray, 50, 150)
    edges_mask = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    # Brown in HSV (low saturation, low value with red-ish hue)
    h_channel = hsv[:, :, 0]
    s_channel = hsv[:, :, 1]
    v_channel = hsv[:, :, 2]
    brown_mask = (h_channel < 30) & (s_channel > 30) & (v_channel < 200)
    brown_edges = np.count_nonzero(edges_mask & brown_mask)
    findings['brown_edge_pixels'] = int(brown_edges)
    if brown_edges > (w * h * 0.0005):
        findings['burn_suspected'] = True
        findings['burn_confidence'] = round(min(0.95, brown_edges / (w * h * 0.01)), 2)
    else:
        findings['burn_suspected'] = False
        findings['burn_confidence'] = 0.0

    # Heuristic: dark spots (possible mold or pest clusters)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    _, th = cv2.threshold(blur, max(0, int(np.mean(blur) - 30)), 255, cv2.THRESH_BINARY_INV)
    # Remove small noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    spot_count = 0
    spot_area = 0
    for c in contours:
        area = cv2.contourArea(c)
        if area > 20 and area < (w * h * 0.05):
            spot_count += 1
            spot_area += area
    findings['spot_count'] = int(spot_count)
    findings['spot_total_area'] = int(spot_area)
    if spot_count >= 3 or (spot_area > (w * h * 0.001)):
        findings['spots_suspected'] = True
        findings['spots_confidence'] = round(min(0.98, spot_area / (w * h * 0.02)), 2)
    else:
        findings['spots_suspected'] = False
        findings['spots_confidence'] = 0.0

    # Heuristic: light stress (over-exposure or under-exposure detection)
    bright_pixels = np.count_nonzero(v_channel > 240)
    dark_pixels = np.count_nonzero(v_channel < 30)
    findings['bright_pixel_ratio'] = round(float(bright_pixels) / (w * h), 4)
    findings['dark_pixel_ratio'] = round(float(dark_pixels) / (w * h), 4)
    if findings['bright_pixel_ratio'] > 0.05:
        findings['light_stress_overexposed'] = True
        findings['light_over_confidence'] = round(min(0.95, findings['bright_pixel_ratio'] * 5), 2)
    else:
        findings['light_stress_overexposed'] = False
        findings['light_over_confidence'] = 0.0

    if findings['dark_pixel_ratio'] > 0.1:
        findings['light_stress_underexposed'] = True
        findings['light_under_confidence'] = round(min(0.95, findings['dark_pixel_ratio'] * 3), 2)
    else:
        findings['light_stress_underexposed'] = False
        findings['light_under_confidence'] = 0.0

    # Annotate image with findings
    annotated = img.copy()
    y0 = 20
    for key, val in list(findings.items())[:8]:
        cv2.putText(annotated, f"{key}: {val}", (10, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1)
        y0 += 16

    annotated_path = path + ".annotated.jpg"
    if save_annotated:
        cv2.imencode('.jpg', annotated)[1].tofile(annotated_path)

    findings['annotated_image'] = annotated_path
    findings['image_size'] = (w, h)
    return findings
