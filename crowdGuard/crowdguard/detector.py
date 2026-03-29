from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


@dataclass
class Detection:
    bbox: list[int]
    confidence: float


class CrowdDetector:
    def __init__(self, model_path: str, confidence_threshold: float = 0.45, iou_threshold: float = 0.45):
        package_root = Path(__file__).resolve().parents[1]
        os.environ.setdefault("YOLO_CONFIG_DIR", str(package_root / ".yolo_config"))
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.model = YOLO(model_path)

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self.model(
            frame,
            classes=[0],
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )
        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                detections.append(
                    Detection(
                        bbox=[int(x1), int(y1), int(x2), int(y2)],
                        confidence=confidence,
                    )
                )
        return detections

    @staticmethod
    def draw(frame: np.ndarray, detections: list[Detection], color: tuple[int, int, int]) -> np.ndarray:
        output = frame.copy()
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                output,
                f"{detection.confidence:.2f}",
                (x1, max(16, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )
        return output
