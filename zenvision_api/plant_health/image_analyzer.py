"""Simple image analysis heuristics for plant health detection.
Detects: yellowing (nutrient deficiency/burn), brown edges (burn),
spots/mold/pests, and light stress (over/under exposure).
"""

import cv2
import numpy as np
from typing import Dict, Tuple


def _to_native(v):
    """Recursively convert numpy scalars/arrays to native Python types."""
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, dict):
        return {k: _to_native(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return type(v)(_to_native(i) for i in v)
    return v


def _load_image(path: str):
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Unable to load image: {path}")
    return img


def _extract_plant_mask(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    bgr = img.astype(np.float32)
    exg = 2 * bgr[:, :, 1] - bgr[:, :, 0] - bgr[:, :, 2]

    green_mask = (
        (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 95) &
        (hsv[:, :, 1] > 50) & (hsv[:, :, 2] > 40)
    )
    yellow_mask = (
        (hsv[:, :, 0] >= 15) & (hsv[:, :, 0] <= 55) &
        (hsv[:, :, 1] > 40) & (hsv[:, :, 2] > 45)
    )
    exg_mask = exg > 15
    mask = (green_mask | yellow_mask | exg_mask).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        mask = np.zeros_like(mask)
        if cv2.contourArea(largest) > (img.shape[0] * img.shape[1] * 0.002):
            cv2.drawContours(mask, [largest], -1, 255, thickness=cv2.FILLED)
    return mask.astype(bool)


def analyze_image(path: str, save_annotated: bool = True) -> Dict:
    img = _load_image(path)
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    plant_mask = _extract_plant_mask(img)
    plant_pixels = np.count_nonzero(plant_mask)
    image_area = w * h
    vegetation_coverage = round(float(plant_pixels) / max(1, image_area), 4)

    findings = {
        'plant_pixel_count': int(plant_pixels),
        'vegetation_coverage': vegetation_coverage,
    }

    mask_uint8 = plant_mask.astype(np.uint8) * 255
    if plant_pixels:
        mean_b, mean_g, mean_r, _ = cv2.mean(img, mask=mask_uint8)
        green_ratio = mean_g / max((mean_r + mean_b) / 2.0, 1e-6)
        findings['green_ratio'] = round(float(green_ratio), 3)

        hue = hsv[:, :, 0]
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]

        yellow_pixels = np.count_nonzero(
            (hue >= 15) & (hue <= 55) & (sat > 40) & (val > 50) & plant_mask
        )
        yellow_ratio = yellow_pixels / plant_pixels
        findings['yellowing_suspected'] = yellow_ratio > 0.08 or green_ratio < 0.82
        findings['yellowing_confidence'] = round(
            min(0.98, max(yellow_ratio * 1.6, (0.82 - green_ratio) * 1.4, 0.0)), 2
        ) if findings['yellowing_suspected'] else 0.0

        edges = cv2.Canny(gray, 50, 150)
        edges_mask = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
        brown_mask = (hue < 30) & (sat > 35) & (val < 190) & plant_mask
        brown_edges = np.count_nonzero(edges_mask & brown_mask)
        findings['brown_edge_pixels'] = int(brown_edges)
        findings['burn_suspected'] = brown_edges > max(18, plant_pixels * 0.0025)
        findings['burn_confidence'] = round(
            min(0.95, brown_edges / max(1, plant_pixels * 0.011)), 2
        ) if findings['burn_suspected'] else 0.0

        blur = cv2.GaussianBlur(gray, (7, 7), 0)
        plant_mean = float(np.mean(gray[plant_mask]))
        _, th = cv2.threshold(blur, max(0, int(plant_mean - 25)), 255, cv2.THRESH_BINARY_INV)
        th = cv2.bitwise_and(th, th, mask=mask_uint8)
        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        spot_count = 0
        spot_area = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 20 and area < (plant_pixels * 0.08):
                spot_count += 1
                spot_area += area

        findings['spot_count'] = int(spot_count)
        findings['spot_total_area'] = int(spot_area)
        findings['spots_suspected'] = spot_count >= 2 or (spot_area > plant_pixels * 0.001)
        findings['spots_confidence'] = round(
            min(0.98, spot_area / max(1, plant_pixels * 0.02)), 2
        ) if findings['spots_suspected'] else 0.0

        bright_pixels = np.count_nonzero((val > 240) & plant_mask)
        dark_pixels = np.count_nonzero((val < 35) & plant_mask)
        findings['bright_pixel_ratio'] = round(float(bright_pixels) / plant_pixels, 4)
        findings['dark_pixel_ratio'] = round(float(dark_pixels) / plant_pixels, 4)

        findings['light_stress_overexposed'] = findings['bright_pixel_ratio'] > 0.06
        findings['light_over_confidence'] = round(
            min(0.95, findings['bright_pixel_ratio'] * 6), 2
        ) if findings['light_stress_overexposed'] else 0.0

        findings['light_stress_underexposed'] = findings['dark_pixel_ratio'] > 0.1
        findings['light_under_confidence'] = round(
            min(0.95, findings['dark_pixel_ratio'] * 4), 2
        ) if findings['light_stress_underexposed'] else 0.0
    else:
        findings.update({
            'green_ratio': 0.0,
            'yellowing_suspected': False,
            'yellowing_confidence': 0.0,
            'brown_edge_pixels': 0,
            'burn_suspected': False,
            'burn_confidence': 0.0,
            'spot_count': 0,
            'spot_total_area': 0,
            'spots_suspected': False,
            'spots_confidence': 0.0,
            'bright_pixel_ratio': 0.0,
            'dark_pixel_ratio': 0.0,
            'light_stress_overexposed': False,
            'light_over_confidence': 0.0,
            'light_stress_underexposed': False,
            'light_under_confidence': 0.0,
        })

    annotated = img.copy()
    y0 = 20
    for key, val in list(findings.items())[:10]:
        cv2.putText(annotated, f"{key}: {val}", (10, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1)
        y0 += 18

    annotated_path = path + ".annotated.jpg"
    if save_annotated:
        cv2.imencode('.jpg', annotated)[1].tofile(annotated_path)

    findings['annotated_image'] = annotated_path
    findings['image_size'] = (w, h)
    return _to_native(findings)
