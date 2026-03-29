from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path


class AlertLogger:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.warning_csv = self.log_dir / "stampede_warning_alerts.csv"
        self.critical_csv = self.log_dir / "stampede_critical_alerts.csv"
        self.metrics_csv = self.log_dir / f"crowd_metrics_{datetime.now().strftime('%Y-%m-%d')}.csv"
        self.status_json = self.log_dir / "latest_status.json"
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

    def write_status(self, payload: dict[str, object]) -> None:
        with self.status_json.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
