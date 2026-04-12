"""
PlantNet API v2 — species identification stage.
Called before the disease model to identify what plant we're looking at.
Requires PLANTNET_API_KEY env var (free tier: 500 req/day at my.plantnet.org).
"""

import os
import requests

_PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"
_TIMEOUT = 15  # seconds


def identify_species(image_path: str) -> dict | None:
    """
    Call PlantNet v2 to identify the plant species in an image.

    Returns a dict with:
        common_name     str   e.g. "Sacred Lotus"
        scientific_name str   e.g. "Nelumbo nucifera"
        confidence      float 0.0–1.0
        is_plant        bool

    Returns None if:
        - PLANTNET_API_KEY is not set
        - no results returned
        - any network/API error
    """
    api_key = os.environ.get("PLANTNET_API_KEY", "")
    if not api_key:
        return None

    try:
        with open(image_path, "rb") as f:
            image_data = f.read()

        resp = requests.post(
            _PLANTNET_URL,
            params={
                "api-key": api_key,
                "include-related-images": "false",
            },
            files={"images": ("image.jpg", image_data, "image/jpeg")},
            data={"organs": "auto"},
            timeout=_TIMEOUT,
        )

        # 404 means PlantNet couldn't identify the species — not that it's definitely
        # not a plant. Return None so the ONNX disease model runs without interference.
        if resp.status_code == 404:
            return None

        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            return None

        top = results[0]
        confidence = round(float(top.get("score", 0.0)), 4)
        species = top.get("species", {})
        scientific_name = species.get("scientificNameWithoutAuthor", "Unknown")
        common_names = species.get("commonNames") or []
        common_name = common_names[0] if common_names else scientific_name

        return {
            "is_plant": True,
            "common_name": common_name,
            "scientific_name": scientific_name,
            "confidence": confidence,
        }

    except Exception:
        # Network errors, bad JSON, unexpected schema — degrade gracefully
        return None
