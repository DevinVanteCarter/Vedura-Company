"""
Species identification — two-stage pipeline:

  Stage 1: Claude Vision (claude-haiku-4-5) — identifies any plant from any photo.
           Requires ANTHROPIC_API_KEY. Fast, reliable, understands garden photos.

  Stage 2: PlantNet API v2 fallback — used if Claude is not available.
           Requires PLANTNET_API_KEY (free tier: 500 req/day at my.plantnet.org).
"""

import base64
import json
import os
import requests

_PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"
_CLAUDE_URL   = "https://api.anthropic.com/v1/messages"
_TIMEOUT      = 20


def _identify_with_claude(image_path: str) -> dict | None:
    """
    Use Claude Vision to identify the plant species from any photo.
    Returns the same dict shape as identify_species, or None on failure.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    try:
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Detect media type from file header
        if image_data[:4] == b'\x89PNG':
            media_type = "image/png"
        elif image_data[:6] in (b'GIF87a', b'GIF89a'):
            media_type = "image/gif"
        elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
            media_type = "image/webp"
        else:
            media_type = "image/jpeg"

        b64 = base64.standard_b64encode(image_data).decode("utf-8")

        prompt = (
            "You are a plant identification expert. Look at this image and identify the plant.\n\n"
            "Respond with ONLY a JSON object — no markdown, no explanation:\n"
            '{"is_plant": true/false, "common_name": "...", "scientific_name": "...", "confidence": 0.0-1.0}\n\n'
            "Rules:\n"
            "- is_plant: false only if there is clearly no plant in the image\n"
            "- common_name: the most recognisable common name (e.g. 'Strawberry', 'Tomato', 'Basil')\n"
            "- scientific_name: genus species (e.g. 'Fragaria × ananassa')\n"
            "- confidence: your confidence 0.0 to 1.0\n"
            "- If multiple plants are visible, identify the most prominent one"
        )

        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 120,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text",  "text": prompt},
                ]
            }]
        }

        resp = requests.post(
            _CLAUDE_URL,
            headers={
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json=payload,
            timeout=_TIMEOUT,
        )

        if resp.status_code != 200:
            return None

        text = resp.json()["content"][0]["text"].strip()
        # Strip markdown fences if Claude wrapped the JSON
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)

        return {
            "is_plant":      bool(data.get("is_plant", True)),
            "common_name":   data.get("common_name") or None,
            "scientific_name": data.get("scientific_name") or None,
            "confidence":    float(data.get("confidence", 0.7)),
        }

    except Exception:
        return None


def _identify_with_plantnet(image_path: str) -> dict | None:
    """PlantNet v2 fallback."""
    api_key = os.environ.get("PLANTNET_API_KEY", "")
    if not api_key:
        return None

    try:
        with open(image_path, "rb") as f:
            image_data = f.read()

        resp = requests.post(
            _PLANTNET_URL,
            params={"api-key": api_key, "include-related-images": "false"},
            files={"images": ("image.jpg", image_data, "image/jpeg")},
            data={"organs": "auto"},
            timeout=_TIMEOUT,
        )

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
            "is_plant":      True,
            "common_name":   common_name,
            "scientific_name": scientific_name,
            "confidence":    confidence,
        }

    except Exception:
        return None


def identify_species(image_path: str) -> dict | None:
    """
    Identify the plant species in an image.

    Tries Claude Vision first (works with any garden photo), then PlantNet.
    Returns None if both fail, so the ONNX disease model runs unhindered.

    Return shape:
        {"is_plant": bool, "common_name": str|None, "scientific_name": str|None, "confidence": float}
    """
    result = _identify_with_claude(image_path)
    if result is not None:
        return result

    return _identify_with_plantnet(image_path)
