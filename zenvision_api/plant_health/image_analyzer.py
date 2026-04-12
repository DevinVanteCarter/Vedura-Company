"""
Plant health analysis — ONNX MobileNetV2 trained on PlantVillage (38 disease classes).
Falls back to OpenCV HSV heuristics if model file is not present.

Pipeline:
  1. Plant.id API v3 — species identification (if PLANT_ID_API_KEY is set)
  2. ONNX PlantVillage model — disease detection for supported crops
  3. CV fallback — HSV heuristics when ONNX model is unavailable
"""

import json
import logging
import os
import numpy as np
import cv2
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from plant_health.species_identifier import identify_species

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Model paths
# ─────────────────────────────────────────────

_MODEL_DIR  = Path(__file__).parent / "models"
_ONNX_PATH  = _MODEL_DIR / "plant_disease_mobilenetv2.onnx"
_CLASS_PATH = _MODEL_DIR / "class_names.json"

# ─────────────────────────────────────────────
# ImageNet normalization constants
# ─────────────────────────────────────────────

_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# ─────────────────────────────────────────────
# Disease classification tables
# ─────────────────────────────────────────────

# Indices of healthy classes in the 38-class PlantVillage label set
_HEALTHY_INDICES = {3, 4, 6, 10, 14, 17, 19, 22, 23, 24, 27, 37}

# Visually yellowing diseases (chlorosis, virus mottling)
_YELLOWING_INDICES = {15, 35, 36}

# Burn / blight / bacterial lesion diseases
_BURN_BLIGHT_INDICES = {0, 2, 8, 9, 16, 18, 20, 21, 26, 28, 29, 30, 34}

# Spots / mold / mite diseases
_SPOTS_MOLD_INDICES = {1, 5, 7, 11, 12, 13, 25, 31, 32, 33}

# Minimum confidence to trust a disease detection
_CONFIDENCE_THRESHOLD = 0.70

# Per-class metadata: (species, disease_or_None)
# disease=None means the class is a healthy variant
_CLASS_META = {
    0:  ("Apple",       "Scab"),
    1:  ("Apple",       "Black Rot"),
    2:  ("Apple",       "Cedar Apple Rust"),
    3:  ("Apple",       None),
    4:  ("Blueberry",   None),
    5:  ("Cherry",      "Powdery Mildew"),
    6:  ("Cherry",      None),
    7:  ("Corn",        "Cercospora and Gray Leaf Spot"),
    8:  ("Corn",        "Common Rust"),
    9:  ("Corn",        "Northern Leaf Blight"),
    10: ("Corn",        None),
    11: ("Grape",       "Black Rot"),
    12: ("Grape",       "Esca (Black Measles)"),
    13: ("Grape",       "Isariopsis Leaf Spot"),
    14: ("Grape",       None),
    15: ("Orange",      "Citrus Greening"),
    16: ("Peach",       "Bacterial Spot"),
    17: ("Peach",       None),
    18: ("Bell Pepper", "Bacterial Spot"),
    19: ("Bell Pepper", None),
    20: ("Potato",      "Early Blight"),
    21: ("Potato",      "Late Blight"),
    22: ("Potato",      None),
    23: ("Raspberry",   None),
    24: ("Soybean",     None),
    25: ("Squash",      "Powdery Mildew"),
    26: ("Strawberry",  "Leaf Scorch"),
    27: ("Strawberry",  None),
    28: ("Tomato",      "Bacterial Spot"),
    29: ("Tomato",      "Early Blight"),
    30: ("Tomato",      "Late Blight"),
    31: ("Tomato",      "Leaf Mold"),
    32: ("Tomato",      "Septoria Leaf Spot"),
    33: ("Tomato",      "Spider Mites"),
    34: ("Tomato",      "Target Spot"),
    35: ("Tomato",      "Yellow Leaf Curl Virus"),
    36: ("Tomato",      "Mosaic Virus"),
    37: ("Tomato",      None),
}

# Crops the model was trained on
SUPPORTED_SPECIES = [
    "Apple", "Blueberry", "Cherry", "Corn (Maize)", "Grape",
    "Orange", "Peach", "Bell Pepper", "Potato", "Raspberry",
    "Soybean", "Squash", "Strawberry", "Tomato",
]

# Organic-first treatment per class index
_TREATMENTS: Dict[int, str] = {
    0:  "Remove infected leaves; apply neem oil spray (2 tbsp/gal) every 7 days; improve air circulation; avoid overhead watering.",
    1:  "Prune infected branches 6 in below visible disease; remove mummified fruit; apply copper fungicide; clean up all debris.",
    2:  "Remove nearby juniper/cedar hosts if possible; apply sulfur fungicide in spring; plant rust-resistant varieties long-term.",
    3:  "Plant looks healthy — keep up current care.",
    4:  "Plant looks healthy — keep up current care.",
    5:  "Spray diluted baking soda (1 tbsp/gal) or neem oil; improve airflow; avoid nitrogen-heavy fertilizers that encourage soft growth.",
    6:  "Plant looks healthy — keep up current care.",
    7:  "Remove heavily infected lower leaves; ensure adequate plant spacing; apply copper fungicide if severe; rotate crops next season.",
    8:  "Apply neem oil or sulfur dust for organic control; copper fungicide for severe cases; plant rust-resistant varieties.",
    9:  "Remove infected leaves; apply copper fungicide; improve field drainage; rotate with non-corn crops next season.",
    10: "Plant looks healthy — keep up current care.",
    11: "Remove and destroy all infected fruit and leaves immediately — they are the primary spore source. Apply copper or sulfur fungicide every 10–14 days.",
    12: "No organic cure exists — remove infected wood during winter pruning; protect wounds with pruning sealant; keep vines stress-free.",
    13: "Apply copper-based fungicide at first sign; remove infected leaves; improve air circulation through canopy management.",
    14: "Plant looks healthy — keep up current care.",
    15: "No cure for citrus greening (HLB). Remove infected trees to prevent spread; control Asian citrus psyllid with neem oil; report to your county extension office.",
    16: "Apply copper hydroxide in late dormancy and early spring; avoid overhead irrigation; prune for airflow; plant resistant varieties.",
    17: "Plant looks healthy — keep up current care.",
    18: "Remove infected leaves and fruit; apply copper-based bactericide; avoid working plants when wet; rotate peppers annually.",
    19: "Plant looks healthy — keep up current care.",
    20: "Remove infected lower leaves; apply copper fungicide or neem oil; mulch to prevent soil splash; water at the base, not the foliage.",
    21: "Act immediately — Late Blight spreads fast. Remove all infected material; apply copper fungicide every 5–7 days in wet weather. Do not compost infected tissue.",
    22: "Plant looks healthy — keep up current care.",
    23: "Plant looks healthy — keep up current care.",
    24: "Plant looks healthy — keep up current care.",
    25: "Spray with baking soda solution (1 tbsp + 1 tsp dish soap/gal) or neem oil; improve airflow; water at the base only; remove severely infected leaves.",
    26: "Remove infected leaves; apply copper fungicide; ensure good air circulation; renovate bed every 3 years.",
    27: "Plant looks healthy — keep up current care.",
    28: "Remove infected leaves; apply copper spray every 7–10 days; avoid overhead watering; rotate tomatoes — do not plant in the same spot for 2–3 years.",
    29: "Remove lower infected leaves; mulch heavily to stop soil splash; apply copper fungicide or neem oil every 7–14 days; water at the base.",
    30: "Immediately remove all infected tissue and bag it — do not compost. Apply copper fungicide. If widespread, consider removing the entire plant to protect others.",
    31: "Increase ventilation; reduce humidity; apply copper fungicide; remove infected leaves; avoid overhead watering.",
    32: "Remove infected leaves starting from the bottom; apply copper or neem oil spray weekly; mulch soil; rotate tomatoes next season.",
    33: "Spray with a strong jet of water to dislodge mites; apply neem oil or insecticidal soap; increase humidity — mites hate moisture; consider introducing predatory mites (Phytoseiulus persimilis).",
    34: "Remove infected leaves; apply copper fungicide; avoid overhead watering; improve air circulation.",
    35: "No cure. Remove infected plants to prevent whitefly spread; control whiteflies with yellow sticky traps and neem oil; use reflective mulch.",
    36: "No cure. Remove infected plants; wash hands and tools thoroughly after handling — this virus spreads by contact; plant resistant varieties.",
    37: "Plant looks healthy — keep up current care.",
}

_HEALTHY_TREATMENT = "Plant looks healthy — keep up current care."

# ─────────────────────────────────────────────
# Module-level ONNX session (loaded once)
# ─────────────────────────────────────────────

_session = None
_class_names: Optional[List[str]] = None
_model_available = False


def _init_model() -> bool:
    """Load ONNX model and class names once at module startup."""
    global _session, _class_names, _model_available

    if not _ONNX_PATH.exists():
        logger.warning("ONNX model not found at %s — using CV fallback", _ONNX_PATH)
        return False
    if not _CLASS_PATH.exists():
        logger.warning("class_names.json not found at %s — using CV fallback", _CLASS_PATH)
        return False

    try:
        import onnxruntime as ort
        _session = ort.InferenceSession(
            str(_ONNX_PATH),
            providers=["CPUExecutionProvider"],
        )
        with open(_CLASS_PATH) as f:
            _class_names = json.load(f)
        _model_available = True
        logger.info("PlantVillage ONNX model loaded (%d classes)", len(_class_names))
        return True
    except Exception as e:
        logger.warning("Failed to load ONNX model: %s — using CV fallback", e)
        return False


# Attempt to load at import time
_init_model()


# ─────────────────────────────────────────────
# Preprocessing
# ─────────────────────────────────────────────

def _preprocess(path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load image, return (onnx_input (1,3,224,224) float32, original_bgr).
    """
    raw = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Cannot load image: {path}")

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_LINEAR)
    arr = resized.astype(np.float32) / 255.0
    arr = (arr - _MEAN) / _STD
    arr = arr.transpose(2, 0, 1)[np.newaxis, :]  # (1, 3, 224, 224)
    return arr, img


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


# ─────────────────────────────────────────────
# ML inference
# ─────────────────────────────────────────────

def _run_ml(path: str, species_hint: Optional[str] = None) -> Optional[Dict]:
    """
    Run ONNX inference. Returns findings dict or None on failure.

    species_hint: if PlantNet already confirmed a supported crop (e.g. "Tomato"),
    re-rank by filtering probabilities to only that species' classes. This lets
    the disease model focus without competing against unrelated crops.
    """
    if not _model_available or _session is None:
        return None

    try:
        input_tensor, orig_img = _preprocess(path)
        logits = _session.run(None, {"pixel_values": input_tensor})[0][0]
        probs = _softmax(logits)

        # ── Species-filtered re-ranking when PlantNet confirmed the crop ──
        if species_hint:
            species_indices = [
                i for i, (sp, _) in _CLASS_META.items()
                if sp and sp.lower() == species_hint.lower()
            ]
            if species_indices:
                # Renormalise within species classes only
                species_probs = np.zeros_like(probs)
                for i in species_indices:
                    species_probs[i] = probs[i]
                total = species_probs.sum()
                if total > 0:
                    species_probs = species_probs / total
                # Use renormalised probs for ranking; keep raw probs for aggregate signals
                rank_probs = species_probs
            else:
                rank_probs = probs
        else:
            rank_probs = probs

        top3_idx = rank_probs.argsort()[::-1][:3]
        top3 = [
            {"class_name": _class_names[i], "confidence": round(float(rank_probs[i]), 4)}
            for i in top3_idx
        ]

        top_idx = int(top3_idx[0])
        top_conf = float(rank_probs[top_idx])
        top_name = _class_names[top_idx]

        # ── Extract species and clean disease name from top prediction ──
        top_meta = _CLASS_META.get(top_idx, (None, None))
        identified_species = top_meta[0] or "Unknown"
        clean_disease = top_meta[1]  # None if healthy class

        # ── Consistency cross-check (only applies without species hint) ──
        if species_hint:
            inconsistent_species = False
        else:
            top3_species = {_CLASS_META[int(i)][0] for i in top3_idx if int(i) in _CLASS_META}
            inconsistent_species = len(top3_species) >= 3

        # ── Confidence threshold: lower bar when species is already confirmed ──
        # Disease threshold: require 0.50 confidence to name a specific disease.
        # Species threshold: much lower — if the top 3 predictions agree on a crop
        # we report it even at modest confidence.
        disease_threshold = 0.35 if species_hint else 0.50
        low_confidence_disease = top_conf < disease_threshold
        # Species is "unknown" only when the top 3 genuinely disagree on the crop.
        low_confidence_species = inconsistent_species

        if low_confidence_disease or low_confidence_species:
            is_healthy = True
            disease_name = "Healthy"
            # Keep the species from the top prediction unless top-3 are contradictory.
            if inconsistent_species:
                identified_species = "Unknown"
                species_note = "Multiple plant types detected — upload a clearer, closer photo."
            else:
                # Species looks right, just low disease confidence.
                species_note = "Species identified; disease confidence too low for diagnosis."
            severity = "none"
            treatment = _HEALTHY_TREATMENT
            green_ratio = 1.25
            yellowing_conf = burn_conf = spots_conf = 0.0
            healthy_conf = 1.0
        else:
            is_healthy = top_idx in _HEALTHY_INDICES
            disease_name = "Healthy" if is_healthy else (clean_disease or top_name)
            species_note = ""

            yellowing_conf = float(sum(probs[i] for i in _YELLOWING_INDICES))
            burn_conf      = float(sum(probs[i] for i in _BURN_BLIGHT_INDICES))
            spots_conf     = float(sum(probs[i] for i in _SPOTS_MOLD_INDICES))
            healthy_conf   = float(sum(probs[i] for i in _HEALTHY_INDICES))

            # green_ratio proxy
            if is_healthy:
                green_ratio = round(1.2 + healthy_conf * 0.2, 3)
            elif top_idx in _YELLOWING_INDICES:
                green_ratio = round(max(0.4, 1.0 - top_conf * 0.7), 3)
            elif top_idx in _BURN_BLIGHT_INDICES:
                green_ratio = round(max(0.6, 1.1 - top_conf * 0.5), 3)
            else:
                green_ratio = round(max(0.7, 1.15 - top_conf * 0.4), 3)

            if is_healthy:
                severity = "none"
            elif top_conf < 0.5:
                severity = "mild"
            elif top_conf < 0.80:
                severity = "moderate"
            else:
                severity = "severe"

            treatment = _TREATMENTS.get(top_idx, _HEALTHY_TREATMENT)

        # Map to compatibility fields (main.py reads these)
        low_conf_gate = low_confidence_disease or low_confidence_species
        yellowing_suspected = not low_conf_gate and yellowing_conf > 0.25
        burn_suspected      = not low_conf_gate and burn_conf > 0.25
        spots_suspected     = not low_conf_gate and spots_conf > 0.25

        h, w = orig_img.shape[:2]

        return {
            # ── new ML fields ──────────────────────────────────
            "model_used":             "onnx_plantvillage_mobilenetv2",
            "identified_species":     identified_species,
            "disease_name":           disease_name,
            "severity":               severity,
            "treatment":              treatment,
            "top_predictions":        top3,
            "is_healthy":             is_healthy,
            "low_confidence_species": low_confidence_species,
            "species_note":           species_note,
            "supported_species":      SUPPORTED_SPECIES,
            # ── compatibility fields (main.py + health score) ──
            "green_ratio":              green_ratio,
            "yellowing_suspected":      yellowing_suspected,
            "yellowing_confidence":     round(min(0.95, yellowing_conf), 2),
            "burn_suspected":           burn_suspected,
            "burn_confidence":          round(min(0.95, burn_conf), 2),
            "spots_suspected":          spots_suspected,
            "spots_confidence":         round(min(0.95, spots_conf), 2),
            "light_stress_overexposed":  False,
            "light_over_confidence":     0.0,
            "light_stress_underexposed": False,
            "light_under_confidence":    0.0,
            "vegetation_coverage":      1.0,
            "plant_pixel_count":        50000,
            "flower_detected":          False,
            "flower_pixel_ratio":       0.0,
            "brown_edge_pixels":        0,
            "spot_count":               0,
            "spot_total_area":          0,
            "bright_pixel_ratio":       0.0,
            "dark_pixel_ratio":         0.0,
            # ── metadata ───────────────────────────────────────
            "annotated_image": path,
            "image_size":      (w, h),
        }

    except Exception as e:
        logger.error("ML inference failed: %s", e, exc_info=True)
        return None


# ─────────────────────────────────────────────
# CV fallback (kept from original analyzer)
# ─────────────────────────────────────────────

def _to_native(v):
    if isinstance(v, np.bool_):      return bool(v)
    if isinstance(v, np.integer):    return int(v)
    if isinstance(v, np.floating):   return float(v)
    if isinstance(v, np.ndarray):    return v.tolist()
    if isinstance(v, dict):          return {k: _to_native(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)): return type(v)(_to_native(i) for i in v)
    return v


def _extract_plant_mask(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    bgr = img.astype(np.float32)
    exg = 2 * bgr[:, :, 1] - bgr[:, :, 0] - bgr[:, :, 2]
    green_mask  = (hsv[:,:,0] >= 35) & (hsv[:,:,0] <= 95) & (hsv[:,:,1] > 50) & (hsv[:,:,2] > 40)
    yellow_mask = (hsv[:,:,0] >= 15) & (hsv[:,:,0] <= 55) & (hsv[:,:,1] > 40) & (hsv[:,:,2] > 45)
    mask = (green_mask | yellow_mask | (exg > 15)).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=1)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        mask = np.zeros_like(mask)
        if cv2.contourArea(largest) > (img.shape[0] * img.shape[1] * 0.002):
            cv2.drawContours(mask, [largest], -1, 255, thickness=cv2.FILLED)
    return mask.astype(bool)


def _analyze_cv_fallback(path: str, save_annotated: bool = False) -> Dict:
    """Original HSV-based analyzer, used when ONNX model is unavailable."""
    raw = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Cannot load image: {path}")

    h, w = img.shape[:2]
    hsv  = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    plant_mask   = _extract_plant_mask(img)
    plant_pixels = int(np.count_nonzero(plant_mask))
    image_area   = w * h
    vegetation_coverage = round(float(plant_pixels) / max(1, image_area), 4)

    findings: Dict = {
        "model_used":       "cv_fallback",
        "plant_pixel_count": plant_pixels,
        "vegetation_coverage": vegetation_coverage,
    }

    mask_uint8 = plant_mask.astype(np.uint8) * 255

    if plant_pixels:
        mean_b, mean_g, mean_r, _ = cv2.mean(img, mask=mask_uint8)
        green_ratio = mean_g / max((mean_r + mean_b) / 2.0, 1e-6)
        findings["green_ratio"] = round(float(green_ratio), 3)

        hue = hsv[:,:,0]; sat = hsv[:,:,1]; val = hsv[:,:,2]

        yellow_pixels = np.count_nonzero(
            (hue >= 15) & (hue <= 55) & (sat > 40) & (val > 50) & plant_mask
        )
        yellow_ratio = yellow_pixels / plant_pixels
        findings["yellowing_suspected"]  = bool(yellow_ratio > 0.08 or green_ratio < 0.82)
        findings["yellowing_confidence"] = round(
            min(0.98, max(yellow_ratio * 1.6, (0.82 - green_ratio) * 1.4, 0.0)), 2
        ) if findings["yellowing_suspected"] else 0.0

        flower_mask = (((hue <= 15) | (hue >= 150)) & (sat > 60) & (val > 80) & plant_mask)
        flower_pixel_ratio = float(np.count_nonzero(flower_mask)) / plant_pixels
        flower_detected = flower_pixel_ratio > 0.08 and green_ratio > 1.0
        findings["flower_detected"]    = bool(flower_detected)
        findings["flower_pixel_ratio"] = round(flower_pixel_ratio, 3)

        edges = cv2.Canny(gray, 50, 150)
        edges_mask = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
        brown_mask = (hue >= 8) & (hue <= 22) & (sat > 45) & (val > 40) & (val < 185) & plant_mask
        brown_edges = int(np.count_nonzero(edges_mask & brown_mask))
        findings["brown_edge_pixels"] = brown_edges
        findings["burn_suspected"]    = bool(brown_edges > max(30, plant_pixels * 0.004))
        if findings["burn_suspected"]:
            bc = min(0.90, brown_edges / max(1, plant_pixels * 0.015))
            if flower_detected: bc *= 0.5
            findings["burn_confidence"] = round(bc, 2)
        else:
            findings["burn_confidence"] = 0.0

        blur = cv2.GaussianBlur(gray, (7, 7), 0)
        plant_mean = float(np.mean(gray[plant_mask]))
        _, th = cv2.threshold(blur, max(0, int(plant_mean - 25)), 255, cv2.THRESH_BINARY_INV)
        th = cv2.bitwise_and(th, th, mask=mask_uint8)
        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        spot_count = 0; spot_area = 0
        for c in contours:
            area = cv2.contourArea(c)
            if 500 <= area < (plant_pixels * 0.08):
                spot_count += 1; spot_area += int(area)
        findings["spot_count"]       = spot_count
        findings["spot_total_area"]  = spot_area
        findings["spots_suspected"]  = bool(spot_count >= 3 or spot_area > plant_pixels * 0.015)
        avg_spot = (spot_area / spot_count) if spot_count > 0 else 0
        if findings["spots_suspected"]:
            sc = min(0.90, spot_area / max(1, plant_pixels * 0.06))
            if avg_spot < 800 and spot_count > 5: sc *= 0.4
            if flower_detected: sc *= 0.5
            findings["spots_confidence"] = round(sc, 2)
        else:
            findings["spots_confidence"] = 0.0

        bright_pixels = int(np.count_nonzero((val > 240) & plant_mask))
        dark_pixels   = int(np.count_nonzero((val < 35)  & plant_mask))
        findings["bright_pixel_ratio"] = round(float(bright_pixels) / plant_pixels, 4)
        findings["dark_pixel_ratio"]   = round(float(dark_pixels)   / plant_pixels, 4)
        findings["light_stress_overexposed"]  = bool(findings["bright_pixel_ratio"] > 0.06)
        findings["light_over_confidence"]     = round(min(0.95, findings["bright_pixel_ratio"] * 6), 2) if findings["light_stress_overexposed"] else 0.0
        findings["light_stress_underexposed"] = bool(findings["dark_pixel_ratio"] > 0.1)
        findings["light_under_confidence"]    = round(min(0.95, findings["dark_pixel_ratio"] * 4), 2) if findings["light_stress_underexposed"] else 0.0
    else:
        findings.update({
            "green_ratio": 0.0, "yellowing_suspected": False, "yellowing_confidence": 0.0,
            "flower_detected": False, "flower_pixel_ratio": 0.0,
            "brown_edge_pixels": 0, "burn_suspected": False, "burn_confidence": 0.0,
            "spot_count": 0, "spot_total_area": 0, "spots_suspected": False, "spots_confidence": 0.0,
            "bright_pixel_ratio": 0.0, "dark_pixel_ratio": 0.0,
            "light_stress_overexposed": False, "light_over_confidence": 0.0,
            "light_stress_underexposed": False, "light_under_confidence": 0.0,
        })

    findings["disease_name"]    = "Unknown (CV mode)"
    findings["severity"]        = "unknown"
    findings["treatment"]       = "Upgrade to ML model for specific diagnosis."
    findings["top_predictions"] = []
    findings["is_healthy"]      = False
    findings["annotated_image"] = path
    findings["image_size"]      = (w, h)
    return _to_native(findings)


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def _species_in_supported(common_name: Optional[str], scientific_name: Optional[str]) -> Optional[str]:
    """
    Return the matching SUPPORTED_SPECIES string if Plant.id identified a
    PlantVillage crop, else None.  Matching is case-insensitive substring.
    """
    # Aliases not in SUPPORTED_SPECIES but common in Plant.id results
    _ALIASES = {
        "maize": "Corn",
        "corn":  "Corn",
        "zea mays": "Corn",
        "solanum lycopersicum": "Tomato",
        "capsicum annuum": "Bell Pepper",
        "pepper": "Bell Pepper",
        "solanum tuberosum": "Potato",
        "malus": "Apple",
        "prunus persica": "Peach",
        "vitis": "Grape",
        "fragaria": "Strawberry",
        "glycine max": "Soybean",
        "rubus": "Raspberry",
        "cucurbita": "Squash",
    }
    names_to_check = [
        (common_name or "").lower(),
        (scientific_name or "").lower(),
    ]
    for name in names_to_check:
        if not name:
            continue
        for alias, crop in _ALIASES.items():
            if alias in name:
                return crop
        for crop in SUPPORTED_SPECIES:
            if crop.lower() in name:
                return crop
    return None


def _compute_health_score_and_alerts(result: dict):
    """
    Derive health_score (0–100) and alerts (list[str]) from the
    raw analyzer fields.  These two outputs are always consistent:
    an empty alerts list means score >= 70.
    """
    alerts = []
    is_healthy  = result.get("is_healthy", False)
    low_conf    = result.get("low_confidence_species", False)
    severity    = result.get("severity", "unknown")
    disease     = result.get("disease_name", "") or ""
    green_ratio = result.get("green_ratio", 1.0) or 1.0

    # ── Base score from ML severity / healthy flag ────────────
    if is_healthy or low_conf:
        # ML confirmed healthy (or unsupported species → suppress disease).
        # Fine-tune within 70–95 using green_ratio proxy.
        base = 82 + int(min(13, max(-12, (green_ratio - 1.0) * 15)))
        score = max(70, min(95, base))

    elif severity == "none":
        # Severity field says none but is_healthy wasn't set — treat as healthy.
        base = 80 + int(min(10, max(-10, (green_ratio - 1.0) * 12)))
        score = max(70, min(92, base))

    elif severity == "mild":
        score = max(55, min(74, 68 - int(max(0, (1.0 - green_ratio) * 15))))

    elif severity == "moderate":
        score = max(35, min(54, 46))

    elif severity == "severe":
        score = max(10, min(34, 22))

    else:
        # CV fallback — severity == "unknown", use signal-only scoring.
        base = 75 + int(min(10, max(-20, (green_ratio - 1.0) * 15)))
        score = max(55, min(88, base))

    # ── Per-signal penalties and alert strings ────────────────
    # Only emit alerts (and apply penalties) when not suppressed by healthy/low_conf.
    yellowing_conf = result.get("yellowing_confidence", 0.0) or 0.0
    burn_conf      = result.get("burn_confidence", 0.0)      or 0.0
    spots_conf     = result.get("spots_confidence", 0.0)     or 0.0

    if not (is_healthy or low_conf):
        if result.get("yellowing_suspected"):
            pct = int(yellowing_conf * 100)
            alerts.append(f"Leaf yellowing detected — {pct}% confidence")
            score -= min(15, int(yellowing_conf * 20))

        if result.get("burn_suspected"):
            pct = int(burn_conf * 100)
            alerts.append(f"Leaf burn / tip scorch — {pct}% confidence")
            score -= min(12, int(burn_conf * 15))

        if result.get("spots_suspected"):
            pct = int(spots_conf * 100)
            alerts.append(f"Spots or mold present — {pct}% confidence")
            score -= min(12, int(spots_conf * 15))

        if result.get("light_stress_overexposed"):
            alerts.append("Overexposure: possible sunscald or intense direct light")
            score -= 5

        if result.get("light_stress_underexposed"):
            alerts.append("Low light: insufficient photosynthesis conditions")
            score -= 5

        # Prepend the disease name when ML identified a specific disease.
        _known_non_disease = {"Unknown (CV mode)", "Healthy", "N/A", ""}
        if disease not in _known_non_disease:
            sev_label = severity if severity not in ("none", "unknown") else ""
            label = f"{disease}" + (f" ({sev_label})" if sev_label else "")
            alerts.insert(0, label)

    # ── Species note as informational alert ───────────────────
    if low_conf and result.get("species_note"):
        alerts.append(result["species_note"])

    score = max(5, min(100, score))

    # Invariant guard: empty alerts must mean score >= 70.
    if not alerts and score < 70:
        score = 70

    return int(score), alerts


def analyze_image(path: str, save_annotated: bool = True) -> Dict:
    """
    Analyze a plant image for disease.

    Stage 1 — Plant.id species ID (if PLANT_ID_API_KEY set).
    Stage 2 — ONNX PlantVillage disease model (if model file present).
    Stage 3 — CV HSV fallback.

    Plant.id enriches the response with identified_species, scientific_name,
    and common_name.  If Plant.id confirms the plant is NOT a PlantVillage
    crop, low_confidence_species is forced True and disease detection is
    suppressed.
    """
    # ── Stage 1: Species identification ───────────────────────────────────
    species_result = identify_species(path)

    # Pre-check: if PlantNet confirmed a supported crop, pass it as a hint
    # so the disease model filters to that species' classes only.
    species_hint = None
    if species_result and species_result.get("is_plant") is not False:
        matched = _species_in_supported(
            species_result.get("common_name"),
            species_result.get("scientific_name"),
        )
        if matched:
            species_hint = matched

    # ── Stage 2/3: Disease analysis ────────────────────────────────────────
    result = _run_ml(path, species_hint=species_hint)
    if result is None:
        result = _analyze_cv_fallback(path, save_annotated)

    # ── Merge Plant.id species info into result ────────────────────────────
    if species_result is not None and species_result.get("is_plant") is not False:
        plantid_common     = species_result.get("common_name")
        plantid_scientific = species_result.get("scientific_name")
        plantid_conf       = species_result.get("confidence", 0.0)

        result["plantid_common_name"]     = plantid_common
        result["plantid_scientific_name"] = plantid_scientific
        result["plantid_confidence"]      = plantid_conf

        matched_crop = _species_in_supported(plantid_common, plantid_scientific)

        if matched_crop:
            # Plant.id confirmed a supported crop — trust disease model as-is,
            # but override identified_species with the clean crop name.
            result["identified_species"] = matched_crop
        else:
            # Plant.id identified a plant NOT in PlantVillage training set.
            # Suppress disease detection — the disease model is unreliable here.
            friendly_name = plantid_common or plantid_scientific or "Unknown plant"
            result["identified_species"]     = friendly_name
            result["low_confidence_species"] = True
            result["is_healthy"]             = True
            result["disease_name"]           = "Healthy"
            result["severity"]               = "none"
            result["treatment"]              = _HEALTHY_TREATMENT
            result["species_note"]           = (
                f"Identified as {friendly_name} — not a PlantVillage crop. "
                "Disease model does not apply; check visually for issues."
            )
            result["green_ratio"]            = max(result.get("green_ratio", 1.0), 1.2)
            result["yellowing_confidence"]   = 0.0
            result["burn_confidence"]        = 0.0
            result["spots_confidence"]       = 0.0
            result["yellowing_suspected"]    = False
            result["burn_suspected"]         = False
            result["spots_suspected"]        = False

    elif species_result is not None and species_result.get("is_plant") is False:
        # Plant.id says this is not a plant at all.
        result["identified_species"]     = "Not a plant"
        result["low_confidence_species"] = True
        result["is_healthy"]             = True
        result["disease_name"]           = "N/A"
        result["severity"]               = "none"
        result["treatment"]              = "No plant detected in this image."
        result["species_note"]           = "Plant.id did not detect a plant in this image."
        result["plantid_common_name"]     = None
        result["plantid_scientific_name"] = None
        result["plantid_confidence"]      = 0.0

    # ── Stage 4: Derive health_score and alerts ───────────────────────────
    result["health_score"], result["alerts"] = _compute_health_score_and_alerts(result)

    # ── Stage 5: Expose raw analysis fields under "raw" for the frontend ──
    result["raw"] = {k: v for k, v in result.items()
                     if k not in ("health_score", "alerts", "raw")}

    return result
