"""
Plant.id API v3 — species identification stage.
Called before the disease model to identify what plant we're looking at.
"""

import os
import base64
import requests

_PLANT_ID_URL = "https://plant.id/api/v3/identification"
_TIMEOUT = 10  # seconds


def identify_species(image_path: str) -> dict | None:
    """
    Call Plant.id v3 to identify the plant species in an image.

    Returns a dict with:
        common_name     str   e.g. "Sacred Lotus"
        scientific_name str   e.g. "Nelumbo nucifera"
        confidence      float 0.0–1.0
        is_plant        bool

    Returns None if:
        - PLANT_ID_API_KEY is not set
        - is_plant is False
        - any network/API error
    """
    api_key = os.environ.get("PLANT_ID_API_KEY", "")
    if not api_key:
        return None

    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "images": [f"data:image/jpeg;base64,{b64}"],
            "classification_level": "species",
        }

        headers = {
            "Api-Key": api_key,
            "Content-Type": "application/json",
        }

        resp = requests.post(_PLANT_ID_URL, json=payload, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        result = data.get("result", {})

        is_plant_block = result.get("is_plant", {})
        is_plant = is_plant_block.get("binary", False)
        if not is_plant:
            return {"is_plant": False, "common_name": None, "scientific_name": None, "confidence": 0.0}

        suggestions = result.get("classification", {}).get("suggestions", [])
        if not suggestions:
            return {"is_plant": True, "common_name": None, "scientific_name": None, "confidence": 0.0}

        top = suggestions[0]
        scientific_name = top.get("name", "Unknown")
        confidence = float(top.get("probability", 0.0))

        details = top.get("details") or {}
        common_names = details.get("common_names") or []
        common_name = common_names[0] if common_names else scientific_name

        return {
            "is_plant": True,
            "common_name": common_name,
            "scientific_name": scientific_name,
            "confidence": round(confidence, 4),
        }

    except Exception:
        # Network errors, bad JSON, unexpected schema — degrade gracefully
        return None
