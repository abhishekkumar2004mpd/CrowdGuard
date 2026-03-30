from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import cv2


class AlertLogger:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.warning_csv = self.log_dir / "stampede_warning_alerts.csv"
        self.critical_csv = self.log_dir / "stampede_critical_alerts.csv"
        self.metrics_csv = self.log_dir / f"crowd_metrics_{datetime.now().strftime('%Y-%m-%d')}.csv"
        self.snapshot_csv = self.log_dir / f"system_snapshots_{datetime.now().strftime('%Y-%m-%d')}.csv"
        self.error_csv = self.log_dir / f"system_errors_{datetime.now().strftime('%Y-%m-%d')}.csv"
        self.status_json = self.log_dir / "latest_status.json"
        self.raw_frame_path = self.log_dir / "latest_raw.jpg"
        self.annotated_frame_path = self.log_dir / "latest_annotated.jpg"
        self._ensure_files()

    def _ensure_files(self) -> None:
        self._ensure_csv(
            self.warning_csv,
            ["timestamp", "camera_id", "camera_label", "person_count", "safe_capacity", "occupancy_ratio", "density", "area_sq_meters", "message"],
        )
        self._ensure_csv(
            self.critical_csv,
            ["timestamp", "camera_id", "camera_label", "person_count", "safe_capacity", "occupancy_ratio", "density", "area_sq_meters", "message"],
        )
        self._ensure_csv(
            self.metrics_csv,
            ["timestamp", "camera_id", "camera_label", "person_count", "safe_capacity", "occupancy_ratio", "density", "area_sq_meters", "in_count", "out_count", "status"],
        )
        self._ensure_csv(
            self.snapshot_csv,
            ["timestamp", "camera_id", "camera_label", "person_count", "density", "error_count", "last_error", "status"],
        )
        self._ensure_csv(
            self.error_csv,
            ["timestamp", "camera_id", "camera_label", "stage", "message"],
        )

    @staticmethod
    def _ensure_csv(path: Path, header: list[str]) -> None:
        if path.exists():
            return
        with path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(header)

    def log_metric(self, row: list[object]) -> None:
        with self.metrics_csv.open("a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(row)

    def log_alert(self, severity: str, row: list[object]) -> None:
        target = self.warning_csv if severity == "warning" else self.critical_csv
        with target.open("a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(row)

    def log_snapshot(self, row: list[object]) -> None:
        with self.snapshot_csv.open("a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(row)

    def log_error(self, row: list[object]) -> None:
        with self.error_csv.open("a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(row)

    def write_status(self, payload: dict[str, object]) -> None:
        with self.status_json.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def write_frames(self, raw_frame, annotated_frame) -> None:
        cv2.imwrite(str(self.raw_frame_path), raw_frame)
        cv2.imwrite(str(self.annotated_frame_path), annotated_frame)
