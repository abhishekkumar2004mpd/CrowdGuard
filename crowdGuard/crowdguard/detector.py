from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLO


@dataclass
class Detection:
    bbox: list[int]
    confidence: float
    keypoints: list[tuple[int, int]] | None = None
    keypoint_confidences: list[float] | None = None
    tracker_id: int | None = None


@dataclass
class TrackingSummary:
    detections: list[Detection]
    in_count: int = 0
    out_count: int = 0


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
        self._line_zones: dict[str, sv.LineZone] = {}

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

    def track(
        self,
        frame: np.ndarray,
        camera_id: str,
        line_zone_config: dict | None = None,
        imgsz: int = 640,
    ) -> TrackingSummary:
        results = self.model.track(
            frame,
            classes=[0],
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            persist=True,
            tracker="bytetrack.yaml",
            imgsz=imgsz,
            verbose=False,
        )
        detections = self._detections_from_results(results)
        summary = TrackingSummary(detections=detections)

        if line_zone_config and line_zone_config.get("enabled"):
            line_zone = self._get_or_create_line_zone(camera_id, frame, line_zone_config)
            tracked = self._to_supervision_detections(detections)
            line_zone.trigger(tracked)
            summary.in_count = line_zone.in_count
            summary.out_count = line_zone.out_count

        return summary

    def _detections_from_results(self, results) -> list[Detection]:
        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            keypoints = result.keypoints
            tracker_ids = None
            if getattr(result.boxes, "id", None) is not None:
                tracker_ids = result.boxes.id.int().cpu().tolist()
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
                        tracker_id=tracker_ids[index] if tracker_ids and index < len(tracker_ids) else None,
                    )
                )
        return detections

    def _get_or_create_line_zone(self, camera_id: str, frame: np.ndarray, config: dict) -> sv.LineZone:
        if camera_id in self._line_zones:
            return self._line_zones[camera_id]

        height, width = frame.shape[:2]
        start_ratio = config.get("start_ratio", [0.0, 0.5])
        end_ratio = config.get("end_ratio", [1.0, 0.5])
        start = sv.Point(int(width * float(start_ratio[0])), int(height * float(start_ratio[1])))
        end = sv.Point(int(width * float(end_ratio[0])), int(height * float(end_ratio[1])))
        line_zone = sv.LineZone(start=start, end=end)
        self._line_zones[camera_id] = line_zone
        return line_zone

    @staticmethod
    def _to_supervision_detections(detections: list[Detection]) -> sv.Detections:
        if not detections:
            return sv.Detections.empty()

        xyxy = np.array([detection.bbox for detection in detections], dtype=np.float32)
        confidence = np.array([detection.confidence for detection in detections], dtype=np.float32)
        class_id = np.zeros(len(detections), dtype=int)
        tracker_ids = [
            detection.tracker_id if detection.tracker_id is not None else -1
            for detection in detections
        ]
        return sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id,
            tracker_id=np.array(tracker_ids, dtype=int),
        )

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
            if detection.tracker_id is not None:
                cv2.putText(
                    output,
                    f"ID {detection.tracker_id}",
                    (x1, min(y2 + 18, output.shape[0] - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
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
