from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

from .service import CrowdGuardService


class MonitorController:
    def __init__(self, config_path: Path, status_file: Path):
        self.config_path = config_path
        self.status_file = status_file
        self.service = CrowdGuardService(str(config_path))
        self.worker: threading.Thread | None = None
        self.stop_event: threading.Event | None = None
        self.current_source: dict | None = None

    def is_running(self) -> bool:
        return self.worker is not None and self.worker.is_alive()

    def start(self, source_payload: dict) -> dict:
        self.stop()
        self.stop_event = threading.Event()
        self.current_source = source_payload
        self.worker = threading.Thread(
            target=self.service.run_runtime_source,
            args=(source_payload, self.stop_event, False),
            daemon=True,
        )
        self.worker.start()
        return {"status": "started", "source": source_payload}

    def stop(self) -> dict:
        if self.stop_event is not None:
            self.stop_event.set()
        if self.worker is not None and self.worker.is_alive():
            self.worker.join(timeout=3)
        self.worker = None
        self.stop_event = None
        self.current_source = None
        return {"status": "stopped"}

    def state(self) -> dict:
        return {
            "running": self.is_running(),
            "source": self.current_source,
        }


def create_app(status_file: Path, config_path: Path) -> Flask:
    app = Flask(__name__)
    CORS(app)
    raw_frame_file = status_file.parent / "latest_raw.jpg"
    annotated_frame_file = status_file.parent / "latest_annotated.jpg"
    upload_dir = status_file.parent / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    controller = MonitorController(config_path=config_path, status_file=status_file)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "monitor_running": controller.is_running()})

    @app.get("/status")
    def status():
        if not status_file.exists():
            return jsonify({"status": "idle", "message": "No monitoring output yet.", "monitor_running": controller.is_running()})
        with status_file.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        payload["monitor_running"] = controller.is_running()
        payload["active_source"] = controller.current_source
        return jsonify(payload)

    @app.get("/frame/raw")
    def raw_frame():
        if not raw_frame_file.exists():
            return jsonify({"status": "missing", "message": "No raw frame available yet."}), 404
        return send_file(raw_frame_file, mimetype="image/jpeg", max_age=0)

    @app.get("/frame/annotated")
    def annotated_frame():
        if not annotated_frame_file.exists():
            return jsonify({"status": "missing", "message": "No annotated frame available yet."}), 404
        return send_file(annotated_frame_file, mimetype="image/jpeg", max_age=0)

    @app.get("/control/state")
    def control_state():
        return jsonify(controller.state())

    @app.post("/control/stop")
    def control_stop():
        return jsonify(controller.stop())

    @app.post("/control/start")
    def control_start():
        payload = request.get_json(force=True)
        return jsonify(controller.start(payload))

    @app.post("/control/upload")
    def control_upload():
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return jsonify({"status": "error", "message": "No file uploaded."}), 400
        target = upload_dir / uploaded.filename
        uploaded.save(target)
        source_payload = {
            "camera_id": "uploaded_footage",
            "label": uploaded.filename,
            "source_type": "file",
            "source": str(target),
            "enabled": True,
            "area": {
                "name": "Uploaded footage",
                "fallback_area_sq_meters": 80.0,
                "safe_density_per_sq_meter": 2.5,
            },
        }
        return jsonify(controller.start(source_payload))

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="crowdGuard API service")
    parser.add_argument(
        "--status-file",
        default=str(Path(__file__).resolve().parents[1] / "logs" / "latest_status.json"),
        help="Path to the status JSON written by the monitoring service.",
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[1] / "config" / "crowdguard.sample.json"),
        help="Path to the monitoring configuration JSON file.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5001, type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    app = create_app(Path(args.status_file), Path(args.config))
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
