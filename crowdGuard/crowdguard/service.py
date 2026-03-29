from __future__ import annotations

import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import cv2

from .camera_sources import open_camera
from .config import CameraConfig, build_camera_config, load_config
from .detector import CrowdDetector
from .logging_utils import AlertLogger
from .maps import polygon_area_sq_meters, resolve_google_place_metadata
from .risk_engine import estimate_area_sq_meters, evaluate_risk


class CrowdGuardService:
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        model_config = self.config.model
        model_path = os.getenv("YOLO_MODEL_PATH", model_config.get("model_path", "yolov8n.pt"))
        self.detector = CrowdDetector(
            model_path=model_path,
            confidence_threshold=float(model_config.get("confidence_threshold", 0.45)),
            iou_threshold=float(model_config.get("iou_threshold", 0.45)),
            min_keypoints=int(model_config.get("min_keypoints", 5)),
            min_keypoint_confidence=float(model_config.get("min_keypoint_confidence", 0.35)),
        )
        self.processing = self.config.processing
        self.risk_rules = self.config.risk_rules
        self.logger = AlertLogger(Path(self.config.path.parent.parent) / "logs")
        self.alert_cooldowns: dict[str, float] = {}
        self.maps_metadata = resolve_google_place_metadata(self.config.google_maps)

    def run(self) -> None:
        enabled_cameras = [camera for camera in self.config.cameras if camera.enabled]
        if not enabled_cameras:
            raise RuntimeError("No cameras are enabled in the configuration.")

        for camera in enabled_cameras:
            self.run_source(camera)

    def _resolve_area(self, camera: CameraConfig) -> float:
        if camera.area.map_polygon:
            polygon_area = polygon_area_sq_meters(camera.area.map_polygon)
            if polygon_area > 0:
                return polygon_area

        global_area = self.maps_metadata.get("area_sq_meters")
        if global_area:
            return float(global_area)

        return estimate_area_sq_meters(
            camera.area.width_meters,
            camera.area.length_meters,
            camera.area.fallback_area_sq_meters,
        )

    def run_runtime_source(self, source_payload: dict, stop_event=None, display_override: bool | None = None) -> None:
        camera = build_camera_config(source_payload)
        self.run_source(camera, stop_event=stop_event, display_override=display_override)

    def run_source(self, camera: CameraConfig, stop_event=None, display_override: bool | None = None) -> None:
        opened = open_camera(camera.source_type, camera.source)
        if opened is None:
            print(f"[ERROR] Unable to open camera {camera.camera_id} ({camera.label})")
            return

        cap = opened.capture
        area_sq_meters = self._resolve_area(camera)
        frame_skip = max(int(self.processing.get("frame_skip", 1)), 1)
        resize_width = int(self.processing.get("resize_width", 0) or 0)
        display = bool(self.processing.get("display", True)) if display_override is None else display_override
        display_max_width = int(self.processing.get("display_max_width", 1600) or 0)
        display_max_height = int(self.processing.get("display_max_height", 900) or 0)
        display_scale = float(self.processing.get("display_scale", 1.0) or 1.0)
        cooldown_seconds = float(self.processing.get("cooldown_seconds", 120))
        tracking_config = self.processing.get("tracking", {})
        warning_threshold = float(self.risk_rules.get("warning_threshold", 0.85))
        critical_threshold = float(self.risk_rules.get("critical_threshold", 1.0))
        safe_density_per_sq_meter = float(
            camera.area.safe_density_per_sq_meter or self.risk_rules.get("safe_density_per_sq_meter", 2.5)
        )

        print(
            f"[INFO] Camera {camera.camera_id} opened from {opened.resolved_source}. "
            f"Area={area_sq_meters:.2f} sqm"
        )

        frame_index = 0
        while True:
            if stop_event is not None and stop_event.is_set():
                break
            ok, frame = cap.read()
            if not ok:
                print(f"[WARN] Stream ended or frame read failed for {camera.camera_id}")
                break

            frame_index += 1
            if frame_index % frame_skip != 0:
                continue

            if resize_width > 0 and frame.shape[1] > resize_width:
                scale = resize_width / frame.shape[1]
                frame = cv2.resize(frame, (resize_width, int(frame.shape[0] * scale)))

            if tracking_config.get("enabled", False):
                tracking = self.detector.track(
                    frame,
                    camera.camera_id,
                    line_zone_config=tracking_config.get("line_zone", {}),
                    imgsz=int(tracking_config.get("imgsz", 640)),
                )
                detections = tracking.detections
                in_count = tracking.in_count
                out_count = tracking.out_count
            else:
                detections = self.detector.detect(frame)
                in_count = 0
                out_count = 0
            risk = evaluate_risk(
                person_count=len(detections),
                area_sq_meters=area_sq_meters,
                safe_density_per_sq_meter=safe_density_per_sq_meter,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
            )
            annotated = self._annotate_frame(frame, camera, risk, detections, in_count, out_count)
            self.logger.write_frames(frame, annotated)
            self._log_metric(camera, risk, in_count, out_count)
            self._log_alert_if_needed(camera, risk, cooldown_seconds)

            if display:
                display_frame = self._resize_for_display(
                    annotated,
                    max_width=display_max_width,
                    max_height=display_max_height,
                    scale=display_scale,
                )
                cv2.imshow(f"crowdGuard - {camera.label}", display_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        cap.release()
        cv2.destroyAllWindows()

    @staticmethod
    def _resize_for_display(frame, max_width: int, max_height: int, scale: float):
        height, width = frame.shape[:2]
        if width <= 0 or height <= 0:
            return frame

        scale = max(scale, 1.0)

        if max_width > 0 and max_height > 0:
            bounded_scale = min(max_width / width, max_height / height)
            scale = max(scale, bounded_scale)
        elif max_width > 0:
            scale = max(scale, max_width / width)
        elif max_height > 0:
            scale = max(scale, max_height / height)

        new_width = max(int(width * scale), 1)
        new_height = max(int(height * scale), 1)

        if new_width == width and new_height == height:
            return frame

        return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

    def _annotate_frame(self, frame, camera: CameraConfig, risk, detections, in_count: int, out_count: int):
        if risk.status == "CRITICAL":
            color = (0, 0, 255)
        elif risk.status == "WARNING":
            color = (0, 165, 255)
        else:
            color = (0, 255, 0)

        annotated = self.detector.draw(frame, detections, color)
        lines = [
            f"Camera: {camera.label}",
            f"People: {risk.person_count}",
            f"Area: {risk.area_sq_meters:.1f} sqm",
            f"Safe capacity: {risk.safe_capacity}",
            f"Occupancy: {risk.occupancy_ratio * 100:.1f}%",
            f"Density: {risk.density:.2f} person/sqm",
            f"In/Out: {in_count}/{out_count}",
            f"Status: {risk.status}",
        ]

        cv2.rectangle(annotated, (0, 0), (430, 205), (20, 20, 20), -1)
        y = 25
        for line in lines:
            cv2.putText(annotated, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y += 24

        if risk.status != "NORMAL":
            cv2.rectangle(annotated, (0, annotated.shape[0] - 55), (annotated.shape[1], annotated.shape[0]), color, -1)
            cv2.putText(
                annotated,
                risk.message,
                (16, annotated.shape[0] - 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )
        return annotated

    def _log_metric(self, camera: CameraConfig, risk, in_count: int, out_count: int) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.write_status(
            {
                "timestamp": timestamp,
                "camera_id": camera.camera_id,
                "camera_label": camera.label,
                "person_count": risk.person_count,
                "safe_capacity": risk.safe_capacity,
                "occupancy_ratio": round(risk.occupancy_ratio, 4),
                "density": round(risk.density, 4),
                "area_sq_meters": round(risk.area_sq_meters, 2),
                "in_count": in_count,
                "out_count": out_count,
                "status": risk.status,
                "message": risk.message,
            }
        )
        self.logger.log_metric(
            [
                timestamp,
                camera.camera_id,
                camera.label,
                risk.person_count,
                risk.safe_capacity,
                round(risk.occupancy_ratio, 4),
                round(risk.density, 4),
                round(risk.area_sq_meters, 2),
                in_count,
                out_count,
                risk.status,
            ]
        )

    def _log_alert_if_needed(self, camera: CameraConfig, risk, cooldown_seconds: float) -> None:
        if risk.status == "NORMAL":
            return

        key = f"{camera.camera_id}:{risk.status}"
        now = time.time()
        if now - self.alert_cooldowns.get(key, 0) < cooldown_seconds:
            return

        self.alert_cooldowns[key] = now
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        severity = "warning" if risk.status == "WARNING" else "critical"
        self.logger.log_alert(
            severity,
            [
                timestamp,
                camera.camera_id,
                camera.label,
                risk.person_count,
                risk.safe_capacity,
                round(risk.occupancy_ratio, 4),
                round(risk.density, 4),
                round(risk.area_sq_meters, 2),
                risk.message,
            ],
        )
        print(f"[ALERT] {timestamp} {camera.camera_id} {risk.status}: {risk.message}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="crowdGuard monitoring service")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[1] / "config" / "crowdguard.sample.json"),
        help="Path to the configuration JSON file.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    service = CrowdGuardService(args.config)
    service.run()
