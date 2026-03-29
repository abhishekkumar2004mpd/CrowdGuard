from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2


@dataclass
class OpenedCamera:
    capture: cv2.VideoCapture
    resolved_source: Any


def build_source_candidates(source_type: str, source: Any) -> list[Any]:
    source_type = (source_type or "webcam").lower()

    if source_type in {"webcam", "usb"}:
        if isinstance(source, int):
            return [source, 0, 1, 2]
        return [0, 1, 2]

    if source_type in {"rtsp", "ip", "ip_camera", "http", "mjpeg", "file"}:
        return [source]

    if source_type in {"bluetooth", "wireless"}:
        candidates = [source]
        if isinstance(source, int):
            candidates.extend([0, 1, 2])
        return candidates

    return [source]


def open_camera(source_type: str, source: Any) -> OpenedCamera | None:
    for candidate in build_source_candidates(source_type, source):
        cap = cv2.VideoCapture(candidate)
        if cap.isOpened():
            return OpenedCamera(capture=cap, resolved_source=candidate)
        cap.release()
    return None
