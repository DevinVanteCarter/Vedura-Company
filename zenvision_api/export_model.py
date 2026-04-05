#!/usr/bin/env python3
"""
PlantVillage MobileNetV2 → ONNX Export Script
Run once on Mac Studio. Do NOT run on Railway.

Install deps first (one-time):
  pip3 install torch torchvision transformers huggingface_hub onnxscript

Then run from the repo root:
  python3 zenvision_api/export_model.py

Output files (commit these to git):
  zenvision_api/plant_health/models/plant_disease_mobilenetv2.onnx  (~9MB)
  zenvision_api/plant_health/models/class_names.json
"""

import json
import sys
from pathlib import Path

OUT_DIR = Path(__file__).parent / "plant_health" / "models"
ONNX_PATH = OUT_DIR / "plant_disease_mobilenetv2.onnx"
CLASSES_PATH = OUT_DIR / "class_names.json"

# Try these models in order — first one that loads wins
CANDIDATE_MODELS = [
    # 95.4% accuracy, 9.34MB, explicitly trained on PlantVillage 38 classes
    "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification",
    # 97.77% accuracy, 9.26MB, safetensors format
    "ozair23/mobilenet_v2_1.0_224-finetuned-plantdisease",
]


def check_deps():
    missing = []
    for pkg in ["torch", "transformers", "huggingface_hub"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"\nMissing: {', '.join(missing)}")
        print("\nRun:")
        print("  pip3 install torch torchvision transformers huggingface_hub onnxscript")
        sys.exit(1)


def load_model(repo_id: str):
    """Load a transformers MobileNetV2 from HuggingFace. Returns (model, id2label)."""
    from transformers import AutoModelForImageClassification, AutoConfig
    print(f"  Trying {repo_id}...")
    config = AutoConfig.from_pretrained(repo_id)
    model = AutoModelForImageClassification.from_pretrained(repo_id)
    model.eval()
    id2label = config.id2label  # {0: "Apple___Apple_scab", ...}
    print(f"  Loaded ✓  ({len(id2label)} classes)")
    return model, id2label


def export():
    check_deps()

    import torch

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUT_DIR}\n")

    # --- Find a working model ---
    model = None
    id2label = None
    for repo_id in CANDIDATE_MODELS:
        try:
            model, id2label = load_model(repo_id)
            print(f"  Using: {repo_id}\n")
            break
        except Exception as e:
            print(f"  Failed ({e})\n")

    if model is None:
        print("All candidate models failed. Check your internet connection and HuggingFace access.")
        sys.exit(1)

    # Build ordered class names list from id2label
    class_names = [id2label[i] for i in sorted(id2label.keys())]
    print(f"Classes ({len(class_names)}): {class_names[:3]} ... {class_names[-1]}")

    # --- Export to ONNX ---
    print(f"\nExporting to ONNX (opset 12)...")
    dummy_input = torch.randn(1, 3, 224, 224)

    try:
        torch.onnx.export(
            model,
            dummy_input,
            str(ONNX_PATH),
            opset_version=12,
            input_names=["pixel_values"],
            output_names=["logits"],
            do_constant_folding=True,
            dynamic_axes={"pixel_values": {0: "batch_size"}, "logits": {0: "batch_size"}},
        )
    except Exception as e:
        if "onnxscript" in str(e).lower():
            print(f"\nONNX export requires onnxscript:")
            print("  pip3 install onnxscript")
            print("Then re-run this script.")
            sys.exit(1)
        raise

    size_mb = ONNX_PATH.stat().st_size / 1024 / 1024
    print(f"  Exported ✓  ({size_mb:.1f} MB)")

    # --- Save class names ---
    with open(CLASSES_PATH, "w") as f:
        json.dump(class_names, f, indent=2)
    print(f"  Class names saved ✓  ({len(class_names)} classes)")

    # --- Sanity check with onnxruntime ---
    print("\nSanity check...")
    try:
        import onnxruntime as ort
        import numpy as np
        sess = ort.InferenceSession(str(ONNX_PATH), providers=["CPUExecutionProvider"])
        dummy = np.random.randn(1, 3, 224, 224).astype(np.float32)
        out = sess.run(None, {"pixel_values": dummy})
        top_idx = int(np.argmax(out[0][0]))
        print(f"  Inference OK — top class on random input: [{top_idx}] {class_names[top_idx]}")
    except ImportError:
        print("  onnxruntime not installed locally — skipping check (Railway will have it)")
    except Exception as e:
        print(f"  Warning: inference check failed: {e}")

    print(f"""
✅ Export complete.

Files to commit:
  {ONNX_PATH}
  {CLASSES_PATH}

Next: tell Claude Code to update image_analyzer.py and requirements.txt
""")


if __name__ == "__main__":
    export()
