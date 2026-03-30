from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2


@dataclass
class OpenedCamera:
    capture: cv2.VideoCapture
    resolved_source: Any
    source_type: str
    is_live: bool


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
    normalized_type = (source_type or "webcam").lower()
    for candidate in build_source_candidates(source_type, source):
        if normalized_type in {"webcam", "usb", "bluetooth", "wireless"} and isinstance(candidate, int):
            cap = cv2.VideoCapture(candidate, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(candidate)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            is_live = normalized_type not in {"file"}
            return OpenedCamera(
                capture=cap,
                resolved_source=candidate,
                source_type=normalized_type,
                is_live=is_live,
            )
        cap.release()
    return None


def discover_backend_sources(max_webcams: int = 5) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for index in range(max_webcams):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            sources.append(
                {
                    "camera_id": f"backend_webcam_{index}",
                    "label": f"Backend Camera {index}",
                    "source_type": "webcam",
                    "source": index,
                    "kind": "camera",
                    "resolution": f"{width}x{height}" if width and height else "unknown",
                }
            )
        cap.release()

    sources.extend(
        [
            {
                "camera_id": "backend_cctv_stream",
                "label": "Connected CCTV Stream",
                "source_type": "rtsp",
                "source": "",
                "kind": "network",
                "resolution": "network-defined",
            },
            {
                "camera_id": "backend_upload",
                "label": "Uploaded Footage",
                "source_type": "file",
                "source": "",
                "kind": "upload",
                "resolution": "file-defined",
            },
        ]
    )
    return sources
