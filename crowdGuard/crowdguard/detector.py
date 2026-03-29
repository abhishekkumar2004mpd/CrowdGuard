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
    keypoints: list[tuple[int, int]] | None = None
    keypoint_confidences: list[float] | None = None


class CrowdDetector:
    SKELETON = [
        (0, 1), (0, 2),
        (1, 3), (2, 4),
        (5, 6),
        (5, 7), (7, 9),
        (6, 8), (8, 10),
        (5, 11), (6, 12),
        (11, 12),
        (11, 13), (13, 15),
        (12, 14), (14, 16),
    ]

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.45,
        iou_threshold: float = 0.45,
        min_keypoints: int = 5,
        min_keypoint_confidence: float = 0.35,
    ):
        package_root = Path(__file__).resolve().parents[1]
        os.environ.setdefault("YOLO_CONFIG_DIR", str(package_root / ".yolo_config"))
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.min_keypoints = min_keypoints
        self.min_keypoint_confidence = min_keypoint_confidence
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
            keypoints = result.keypoints
            for index, box in enumerate(result.boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                pose_points, pose_confidences = self._extract_keypoints(keypoints, index)
                if not self._passes_pose_threshold(pose_points, pose_confidences):
                    continue
                detections.append(
                    Detection(
                        bbox=[int(x1), int(y1), int(x2), int(y2)],
                        confidence=confidence,
                        keypoints=pose_points,
                        keypoint_confidences=pose_confidences,
                    )
                )
        return detections

    def _extract_keypoints(
        self,
        keypoints,
        index: int,
    ) -> tuple[list[tuple[int, int]] | None, list[float] | None]:
        if keypoints is None or index >= len(keypoints):
            return None, None

        points = keypoints[index].xy[0].cpu().numpy()
        confidences = keypoints[index].conf[0].cpu().numpy()
        pose_points = [(int(x), int(y)) for x, y in points]
        pose_confidences = [float(value) for value in confidences]
        return pose_points, pose_confidences

    def _passes_pose_threshold(
        self,
        keypoints: list[tuple[int, int]] | None,
        confidences: list[float] | None,
    ) -> bool:
        if not keypoints or not confidences:
            return False

        visible = sum(1 for value in confidences if value >= self.min_keypoint_confidence)
        if visible < self.min_keypoints:
            return False

        eye_indices = (1, 2)
        shoulder_indices = (5, 6)
        arm_indices = (7, 8, 9, 10)

        eye_visible = any(confidences[index] >= self.min_keypoint_confidence for index in eye_indices)
        shoulder_visible = any(confidences[index] >= self.min_keypoint_confidence for index in shoulder_indices)
        arm_visible = any(confidences[index] >= self.min_keypoint_confidence for index in arm_indices)

        return shoulder_visible and (eye_visible or arm_visible)

    def draw(self, frame: np.ndarray, detections: list[Detection], color: tuple[int, int, int]) -> np.ndarray:
        output = frame.copy()
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 1)
            self._draw_stick_figure(output, detection, color)
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

    def _draw_stick_figure(self, frame: np.ndarray, detection: Detection, color: tuple[int, int, int]) -> None:
        if not detection.keypoints or not detection.keypoint_confidences:
            return

        for point_a, point_b in self.SKELETON:
            if (
                detection.keypoint_confidences[point_a] >= self.min_keypoint_confidence
                and detection.keypoint_confidences[point_b] >= self.min_keypoint_confidence
            ):
                cv2.line(
                    frame,
                    detection.keypoints[point_a],
                    detection.keypoints[point_b],
                    color,
                    2,
                    cv2.LINE_AA,
                )

        for index in (1, 2, 5, 6, 7, 8, 9, 10):
            if detection.keypoint_confidences[index] >= self.min_keypoint_confidence:
                cv2.circle(frame, detection.keypoints[index], 3, color, -1, cv2.LINE_AA)
