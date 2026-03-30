"""
prepare_dataset.py
──────────────────
Downloads a crowd-specific dataset from Open Images V7 and converts it to
YOLO format for fine-tuning YOLOv8.

Classes downloaded
  Positive  : Person
  Negatives : Clothing, Bag, Luggage and bags, Mannequin, Umbrella,
              Bicycle helmet, Hat (hard negatives that fool COCO-YOLOv8)

Usage
-----
    python prepare_dataset.py                        # download 2 000 images
    python prepare_dataset.py --limit 500            # smaller quick test
    python prepare_dataset.py --skip-download        # re-convert existing data

Requirements
    pip install fiftyone tqdm
"""

import os
import sys
import shutil
import random
import argparse
from pathlib import Path
from tqdm import tqdm

# ─── paths ────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
DATASET_DIR  = BASE_DIR / "dataset"
IMAGES_TRAIN = DATASET_DIR / "images" / "train"
IMAGES_VAL   = DATASET_DIR / "images" / "val"
LABELS_TRAIN = DATASET_DIR / "labels" / "train"
LABELS_VAL   = DATASET_DIR / "labels" / "val"
RAW_DIR      = DATASET_DIR / "_raw"          # staging area for fiftyone data

# Open Images V7 label → YOLO class-id mapping
# class 0 = person   class 1 = object (hard negative)
LABEL_MAP = {
    "Person"         : 0,
    "Clothing"       : 1,
    "Bag"            : 1,
    "Luggage and bags": 1,
    "Mannequin"      : 1,
    "Umbrella"       : 1,
    "Bicycle helmet" : 1,
    "Hat"            : 1,
}

POSITIVE_LABELS  = ["Person"]
NEGATIVE_LABELS  = [k for k in LABEL_MAP if k != "Person"]

TRAIN_SPLIT = 0.80   # 80 % train / 20 % val
RANDOM_SEED = 42


# ──────────────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────────────

def make_dirs():
    for d in [IMAGES_TRAIN, IMAGES_VAL, LABELS_TRAIN, LABELS_VAL, RAW_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def xyxy_to_yolo(x1, y1, x2, y2, img_w, img_h):
    """Convert absolute xyxy bbox to normalised YOLO cx cy w h."""
    cx = ((x1 + x2) / 2) / img_w
    cy = ((y1 + y2) / 2) / img_h
    w  = (x2 - x1) / img_w
    h  = (y2 - y1) / img_h
    # clamp to [0, 1]
    cx, cy, w, h = (max(0.0, min(1.0, v)) for v in (cx, cy, w, h))
    return cx, cy, w, h


def write_yolo_label(label_path: Path, annotations: list):
    """Write a YOLO annotation .txt file."""
    with open(label_path, "w") as f:
        for class_id, cx, cy, w, h in annotations:
            f.write(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")


# ──────────────────────────────────────────────────────────────────────────────
# dataset download via fiftyone
# ──────────────────────────────────────────────────────────────────────────────

def download_open_images(limit: int):
    """Download images from Open Images V7 using fiftyone."""
    try:
        import fiftyone as fo
        import fiftyone.zoo as foz
    except ImportError:
        print("[ERROR] fiftyone is not installed.")
        print("        Run:  pip install fiftyone")
        sys.exit(1)

    all_labels = POSITIVE_LABELS + NEGATIVE_LABELS
    per_class  = max(1, limit // len(all_labels))

    print(f"\n{'─'*60}")
    print(f"  Downloading Open Images V7")
    print(f"  Labels  : {all_labels}")
    print(f"  Per class: {per_class}  |  Total target: {per_class * len(all_labels)}")
    print(f"{'─'*60}\n")

    dataset = foz.load_zoo_dataset(
        "open-images-v7",
        split="train",
        label_types=["detections"],
        classes=all_labels,
        max_samples=per_class * len(all_labels),
        dataset_dir=str(RAW_DIR),
        dataset_name="crowd_control_raw",
        overwrite=True,
    )

    print(f"\n✓ Downloaded {len(dataset)} samples from Open Images V7")
    return dataset


def convert_fiftyone_to_yolo(dataset):
    """
    Walk a fiftyone dataset and emit YOLO-format images + labels
    into the RAW_DIR staging area.
    Returns list of (image_path, label_path) tuples.
    """
    try:
        from PIL import Image as PILImage
    except ImportError:
        print("[ERROR] Pillow not installed. Run: pip install pillow")
        sys.exit(1)

    pairs = []                       # (img_src_path, label_src_path)
    staging_img  = RAW_DIR / "staged_images"
    staging_lbl  = RAW_DIR / "staged_labels"
    staging_img.mkdir(exist_ok=True)
    staging_lbl.mkdir(exist_ok=True)

    print("\nConverting annotations to YOLO format …")

    for sample in tqdm(dataset, desc="Converting"):
        img_path = Path(sample.filepath)
        if not img_path.exists():
            continue

        # Get image dimensions
        try:
            with PILImage.open(img_path) as img:
                img_w, img_h = img.size
        except Exception:
            continue

        if sample.ground_truth is None:
            continue

        yolo_annotations = []
        for det in sample.ground_truth.detections:
            label = det.label
            if label not in LABEL_MAP:
                continue

            class_id = LABEL_MAP[label]
            # fiftyone uses relative [x, y, w, h] from top-left
            rx, ry, rw, rh = det.bounding_box
            x1 = rx * img_w
            y1 = ry * img_h
            x2 = (rx + rw) * img_w
            y2 = (ry + rh) * img_h

            cx, cy, w, h = xyxy_to_yolo(x1, y1, x2, y2, img_w, img_h)
            if w > 0 and h > 0:
                yolo_annotations.append((class_id, cx, cy, w, h))

        if not yolo_annotations:
            continue

        # Copy image and write label
        dst_img = staging_img / img_path.name
        dst_lbl = staging_lbl / (img_path.stem + ".txt")
        shutil.copy2(img_path, dst_img)
        write_yolo_label(dst_lbl, yolo_annotations)
        pairs.append((dst_img, dst_lbl))

    print(f"✓ Converted {len(pairs)} samples with valid annotations")
    return pairs


# ──────────────────────────────────────────────────────────────────────────────
# train / val split
# ──────────────────────────────────────────────────────────────────────────────

def split_and_copy(pairs: list):
    """Shuffle pairs and copy them into train / val directories."""
    random.seed(RANDOM_SEED)
    random.shuffle(pairs)

    n_train = int(len(pairs) * TRAIN_SPLIT)
    train_pairs = pairs[:n_train]
    val_pairs   = pairs[n_train:]

    def _copy_pairs(pair_list, img_dir, lbl_dir, split_name):
        print(f"\nCopying {split_name} split ({len(pair_list)} samples) …")
        for img_src, lbl_src in tqdm(pair_list, desc=split_name):
            shutil.copy2(img_src, img_dir / img_src.name)
            shutil.copy2(lbl_src, lbl_dir / lbl_src.name)

    _copy_pairs(train_pairs, IMAGES_TRAIN, LABELS_TRAIN, "train")
    _copy_pairs(val_pairs,   IMAGES_VAL,   LABELS_VAL,   "val")

    return len(train_pairs), len(val_pairs)


# ──────────────────────────────────────────────────────────────────────────────
# stats
# ──────────────────────────────────────────────────────────────────────────────

def print_stats(n_train: int, n_val: int):
    # Count class instances across labels
    class_counts = {0: 0, 1: 0}
    for split_lbl_dir in [LABELS_TRAIN, LABELS_VAL]:
        for lbl_file in split_lbl_dir.glob("*.txt"):
            with open(lbl_file) as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        cid = int(parts[0])
                        class_counts[cid] = class_counts.get(cid, 0) + 1

    print(f"\n{'═'*60}")
    print("  DATASET PREPARATION COMPLETE")
    print(f"{'═'*60}")
    print(f"  Train images : {n_train}")
    print(f"  Val   images : {n_val}")
    print(f"  Total images : {n_train + n_val}")
    print(f"  Person bboxes (class 0) : {class_counts.get(0, 0)}")
    print(f"  Object bboxes (class 1) : {class_counts.get(1, 0)}")
    print(f"\n  Dataset stored at : {DATASET_DIR.resolve()}")
    print(f"  Next step → run:  python train_model.py")
    print(f"{'═'*60}\n")


# ──────────────────────────────────────────────────────────────────────────────
# fallback: point at your own images if fiftyone is unavailable
# ──────────────────────────────────────────────────────────────────────────────

def manual_mode():
    """
    If you already have images + YOLO-format labels, place them in:
        dataset/_raw/staged_images/*.jpg
        dataset/_raw/staged_labels/*.txt
    Then re-run with  --skip-download  to just do the train/val split.
    """
    staging_img = RAW_DIR / "staged_images"
    staging_lbl = RAW_DIR / "staged_labels"

    imgs = sorted(staging_img.glob("*.jpg")) + sorted(staging_img.glob("*.png"))
    pairs = []
    for img in imgs:
        lbl = staging_lbl / (img.stem + ".txt")
        if lbl.exists():
            pairs.append((img, lbl))

    if not pairs:
        print("[WARN] No staged images found.")
        print(f"       Place your images in : {staging_img}")
        print(f"       Place YOLO labels in  : {staging_lbl}")
        sys.exit(0)

    print(f"✓ Found {len(pairs)} staged samples (skip-download mode)")
    return pairs


# ──────────────────────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Prepare crowd-control dataset")
    parser.add_argument("--limit",          type=int,  default=2000,
                        help="Max images to download (default: 2000)")
    parser.add_argument("--skip-download",  action="store_true",
                        help="Skip download; use existing staged images instead")
    args = parser.parse_args()

    print("="*60)
    print("  CROWD CONTROL — Dataset Preparation")
    print("="*60)

    make_dirs()

    if args.skip_download:
        pairs = manual_mode()
    else:
        dataset = download_open_images(args.limit)
        pairs   = convert_fiftyone_to_yolo(dataset)

    if not pairs:
        print("[ERROR] No valid image-label pairs found. Exiting.")
        sys.exit(1)

    n_train, n_val = split_and_copy(pairs)
    print_stats(n_train, n_val)


if __name__ == "__main__":
    main()
