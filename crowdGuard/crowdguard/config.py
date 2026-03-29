from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass
class CameraAreaConfig:
    name: str
    width_meters: float | None = None
    length_meters: float | None = None
    fallback_area_sq_meters: float = 50.0
    safe_density_per_sq_meter: float = 2.5
    map_polygon: list[list[float]] = field(default_factory=list)


@dataclass
class CameraConfig:
    camera_id: str
    label: str
    source_type: str
    source: Any
    enabled: bool
    area: CameraAreaConfig
    notes: str = ""


@dataclass
class AppConfig:
    raw: dict[str, Any]
    path: Path

    @property
    def model(self) -> dict[str, Any]:
        return self.raw.get("model", {})

    @property
    def processing(self) -> dict[str, Any]:
        return self.raw.get("processing", {})

    @property
    def risk_rules(self) -> dict[str, Any]:
        return self.raw.get("risk_rules", {})

    @property
    def google_maps(self) -> dict[str, Any]:
        return self.raw.get("google_maps", {})

    @property
    def project(self) -> dict[str, Any]:
        return self.raw.get("project", {})

    @property
    def cameras(self) -> list[CameraConfig]:
        items = []
        for camera in self.raw.get("cameras", []):
            items.append(build_camera_config(camera))
        return items


def build_camera_config(camera: dict[str, Any]) -> CameraConfig:
    area = camera.get("area", {})
    return CameraConfig(
        camera_id=camera["camera_id"],
        label=camera.get("label", camera["camera_id"]),
        source_type=camera.get("source_type", "webcam"),
        source=camera.get("source", 0),
        enabled=bool(camera.get("enabled", True)),
        notes=camera.get("notes", ""),
        area=CameraAreaConfig(
            name=area.get("name", camera["camera_id"]),
            width_meters=area.get("width_meters"),
            length_meters=area.get("length_meters"),
            fallback_area_sq_meters=float(area.get("fallback_area_sq_meters", 50.0)),
            safe_density_per_sq_meter=float(area.get("safe_density_per_sq_meter", 2.5)),
            map_polygon=area.get("map_polygon", []),
        ),
    )


def load_config(config_path: str | Path) -> AppConfig:
    config_file = Path(config_path).resolve()
    env_file = config_file.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    with config_file.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    return AppConfig(raw=raw, path=config_file)
