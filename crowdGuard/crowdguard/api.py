from __future__ import annotations

import argparse
import json
from pathlib import Path

from flask import Flask, jsonify, send_file
from flask_cors import CORS


def create_app(status_file: Path) -> Flask:
    app = Flask(__name__)
    CORS(app)
    raw_frame_file = status_file.parent / "latest_raw.jpg"
    annotated_frame_file = status_file.parent / "latest_annotated.jpg"

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/status")
    def status():
        if not status_file.exists():
            return jsonify({"status": "idle", "message": "No monitoring output yet."})
        with status_file.open("r", encoding="utf-8") as handle:
            return jsonify(json.load(handle))

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

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="crowdGuard API service")
    parser.add_argument(
        "--status-file",
        default=str(Path(__file__).resolve().parents[1] / "logs" / "latest_status.json"),
        help="Path to the status JSON written by the monitoring service.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5001, type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    app = create_app(Path(args.status_file))
    app.run(host=args.host, port=args.port, debug=False)
