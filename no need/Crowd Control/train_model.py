"""
train_model.py
──────────────
Fine-tunes yolov8n.pt on the custom 2-class crowd dataset produced by
prepare_dataset.py, then patches config.json to point at the new model.

Usage
-----
    python train_model.py                    # full training run
    python train_model.py --epochs 5         # quick test (fewer epochs)
    python train_model.py --smoke-test       # 1 epoch, 8 images — syntax check only

Output
------
    runs/train/crowd_model/weights/best.pt   ← best checkpoint
    runs/train/crowd_model/weights/last.pt   ← last checkpoint
    runs/train/crowd_model/results.csv       ← per-epoch metrics
    config.json                              ← model_type updated automatically

Requirements
    pip install ultralytics torch torchvision
"""

import os
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime

os.environ.setdefault("YOLO_CONFIG_DIR", str(Path(__file__).parent / ".yolo_config"))

# ─── paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
DATASET_YAML = BASE_DIR / "dataset.yaml"
CONFIG_JSON  = BASE_DIR / "config.json"
BASE_MODEL   = BASE_DIR / "yolov8n.pt"           # starting checkpoint
PROJECT_DIR  = BASE_DIR / "runs" / "train"
RUN_NAME     = "crowd_model"


# ──────────────────────────────────────────────────────────────────────────────
# pre-flight checks
# ──────────────────────────────────────────────────────────────────────────────

def check_prerequisites(smoke: bool):
    errors = []

    if not BASE_MODEL.exists():
        errors.append(f"Base model not found: {BASE_MODEL}\n"
                      "  Run once to download:  python -c \"from ultralytics import YOLO; YOLO('yolov8n.pt')\"")

    if not DATASET_YAML.exists():
        errors.append(f"dataset.yaml not found: {DATASET_YAML}")

    if not smoke:
        # Check that dataset directories actually have images
        for split in ("train", "val"):
            img_dir = BASE_DIR / "dataset" / "images" / split
            if not img_dir.exists() or not any(img_dir.iterdir()):
                errors.append(
                    f"No images found in {img_dir}\n"
                    "  Run first:  python prepare_dataset.py"
                )

    if errors:
        print("\n[ERROR] Pre-flight checks failed:\n")
        for e in errors:
            print(f"  ✗ {e}\n")
        raise SystemExit(1)

    print("✓ Pre-flight checks passed")


# ──────────────────────────────────────────────────────────────────────────────
# smoke-test dataset (1 image per split so trainer doesn't crash)
# ──────────────────────────────────────────────────────────────────────────────

def setup_smoke_dataset(tmp_dir: Path):
    """
    Create a tiny synthetic dataset (8 solid-colour 640×640 images) so the
    training loop can be validated end-to-end without real data.
    """
    import numpy as np

    for split in ("train", "val"):
        img_out = tmp_dir / "images" / split
        lbl_out = tmp_dir / "labels" / split
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        n = 4 if split == "train" else 2
        for i in range(n):
            # Solid-colour image
            colour = [(200, 100, 50), (50, 200, 100)][i % 2]
            img    = np.full((640, 640, 3), colour, dtype="uint8")
            try:
                import cv2
                cv2.imwrite(str(img_out / f"smoke_{i}.jpg"), img)
            except ImportError:
                from PIL import Image
                Image.fromarray(img[:, :, ::-1]).save(img_out / f"smoke_{i}.jpg")

            # Dummy annotation: one person, one object
            with open(lbl_out / f"smoke_{i}.txt", "w") as f:
                f.write("0 0.5 0.5 0.2 0.4\n")   # person
                f.write("1 0.2 0.3 0.1 0.2\n")   # object

    # Write a temporary dataset.yaml pointing to tmp dir
    smoke_yaml = tmp_dir / "smoke_dataset.yaml"
    smoke_yaml.write_text(
        f"path: {tmp_dir.as_posix()}\n"
        "train: images/train\n"
        "val:   images/val\n"
        "nc: 2\n"
        "names:\n"
        "  0: person\n"
        "  1: object\n"
    )
    return smoke_yaml


# ──────────────────────────────────────────────────────────────────────────────
# training
# ──────────────────────────────────────────────────────────────────────────────

def train(epochs: int, batch: int, imgsz: int, dataset_yaml: Path, smoke: bool):
    from ultralytics import YOLO

    print(f"\n{'═'*60}")
    print(f"  CROWD CONTROL — Fine-Tuning YOLOv8n")
    print(f"{'═'*60}")
    print(f"  Base model  : {BASE_MODEL}")
    print(f"  Dataset     : {dataset_yaml}")
    print(f"  Epochs      : {epochs}")
    print(f"  Batch size  : {batch}")
    print(f"  Image size  : {imgsz}")
    print(f"  Smoke test  : {smoke}")
    print(f"{'═'*60}\n")

    model = YOLO(str(BASE_MODEL))

    # ── augmentation hyper-params tuned for dense crowd imagery ──────────────
    results = model.train(
        data        = str(dataset_yaml),
        epochs      = epochs,
        batch       = batch,
        imgsz       = imgsz,
        project     = str(PROJECT_DIR),
        name        = RUN_NAME,
        exist_ok    = True,

        # ── transfer-learning: freeze backbone, train head ──────────────────
        freeze      = 10,          # freeze first 10 layers (backbone)

        # ── augmentation ────────────────────────────────────────────────────
        mosaic      = 1.0,         # 4-image mosaic (great for crowds)
        mixup       = 0.15,        # blend two images (helps clothing negatives)
        flipud      = 0.1,         # occasionally flip upside-down
        fliplr      = 0.5,         # horizontal flip
        hsv_h       = 0.015,       # hue jitter
        hsv_s       = 0.7,         # saturation jitter
        hsv_v       = 0.4,         # value/brightness jitter
        degrees     = 5.0,         # small rotation (people rarely slant >5°)
        translate   = 0.1,         # slight translation
        scale       = 0.5,         # scale jitter (handles different distances)
        shear       = 2.0,         # mild shear

        # ── optimiser ───────────────────────────────────────────────────────
        optimizer   = "AdamW",
        lr0         = 0.001,
        lrf         = 0.01,
        warmup_epochs = 3,
        patience    = 20,          # early-stop after 20 stagnant epochs

        # ── misc ────────────────────────────────────────────────────────────
        workers     = 4,
        device      = "",          # auto-detect GPU/CPU
        verbose     = True,
        save        = True,
        save_period = 10,          # save checkpoint every 10 epochs
        plots       = True,        # save training curves
        rect        = False,       # disable rectangular batching (better mosaic)
        close_mosaic = max(1, epochs // 10),   # disable mosaic in last 10 %
    )

    return results


# ──────────────────────────────────────────────────────────────────────────────
# post-training: update config.json
# ──────────────────────────────────────────────────────────────────────────────

def update_config(best_model_path: Path):
    """Patch config.json so the crowd_control system uses the new model."""
    if not CONFIG_JSON.exists():
        print(f"[WARN] config.json not found at {CONFIG_JSON}. Skipping config update.")
        return

    with open(CONFIG_JSON, "r") as f:
        config = json.load(f)

    # Use relative path so config is portable
    rel_path = best_model_path.relative_to(BASE_DIR).as_posix()

    config.setdefault("detection_settings", {})
    config["detection_settings"]["model_type"]  = rel_path
    config["detection_settings"]["num_classes"] = 2
    config["detection_settings"]["class_names"] = ["person", "object"]

    # Backup the original config
    backup = CONFIG_JSON.with_suffix(f".backup_{datetime.now():%Y%m%d_%H%M%S}.json")
    shutil.copy2(CONFIG_JSON, backup)

    with open(CONFIG_JSON, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✓ config.json updated  →  model_type = \"{rel_path}\"")
    print(f"  Original backed up to: {backup.name}")


# ──────────────────────────────────────────────────────────────────────────────
# print summary
# ──────────────────────────────────────────────────────────────────────────────

def print_summary(results, best_path: Path, smoke: bool):
    print(f"\n{'═'*60}")
    print("  TRAINING COMPLETE" + (" [SMOKE TEST]" if smoke else ""))
    print(f"{'═'*60}")

    # Ultralytics results object exposes metrics
    try:
        metrics = results.results_dict
        map50   = metrics.get("metrics/mAP50(B)",    0.0)
        map5095 = metrics.get("metrics/mAP50-95(B)", 0.0)
        prec    = metrics.get("metrics/precision(B)", 0.0)
        rec     = metrics.get("metrics/recall(B)",    0.0)

        print(f"  mAP@0.5          : {map50:.4f}")
        print(f"  mAP@0.5:0.95     : {map5095:.4f}")
        print(f"  Precision        : {prec:.4f}")
        print(f"  Recall           : {rec:.4f}")
    except Exception:
        print("  (metrics not available for smoke-test run)")

    print(f"\n  Best model saved : {best_path}")
    print(f"\n  Runtime model selection is config-driven.")
    print(f"  config.json has already been updated to use the trained checkpoint.")
    print(f"{'═'*60}\n")


# ──────────────────────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fine-tune YOLOv8n for crowd detection")
    parser.add_argument("--epochs",      type=int,  default=50,
                        help="Number of training epochs (default: 50)")
    parser.add_argument("--batch",       type=int,  default=16,
                        help="Batch size (default: 16; reduce if OOM)")
    parser.add_argument("--imgsz",       type=int,  default=640,
                        help="Input image size (default: 640)")
    parser.add_argument("--smoke-test",  action="store_true",
                        help="Run 1 epoch on synthetic data (validates pipeline only)")
    args = parser.parse_args()

    smoke = args.smoke_test

    if smoke:
        print("\n[SMOKE TEST] Using synthetic 8-image dataset for 1 epoch …\n")
        tmp_dir      = BASE_DIR / "_smoke_tmp"
        dataset_yaml = setup_smoke_dataset(tmp_dir)
        epochs       = 1
        batch        = 2
        imgsz        = 320
    else:
        check_prerequisites(smoke=False)
        dataset_yaml = DATASET_YAML
        epochs       = args.epochs
        batch        = args.batch
        imgsz        = args.imgsz

    # ── train ─────────────────────────────────────────────────────────────────
    results = train(epochs, batch, imgsz, dataset_yaml, smoke)

    best_path = PROJECT_DIR / RUN_NAME / "weights" / "best.pt"

    if not best_path.exists():
        # Smoke test with 1 epoch may only produce last.pt
        last_path = PROJECT_DIR / RUN_NAME / "weights" / "last.pt"
        if last_path.exists():
            shutil.copy2(last_path, best_path)
            print("[INFO] Only last.pt found; copied to best.pt")
        else:
            print("[WARN] No weights file found. Check training logs.")
            best_path = Path("(not found)")

    # ── patch config ──────────────────────────────────────────────────────────
    if best_path.exists():
        update_config(best_path)

    # ── print summary ─────────────────────────────────────────────────────────
    print_summary(results, best_path, smoke)

    # ── cleanup smoke tmp ─────────────────────────────────────────────────────
    if smoke and (BASE_DIR / "_smoke_tmp").exists():
        shutil.rmtree(BASE_DIR / "_smoke_tmp")
        print("  Smoke-test temp files cleaned up.\n")


if __name__ == "__main__":
    main()
