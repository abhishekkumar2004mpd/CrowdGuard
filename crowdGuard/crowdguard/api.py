from __future__ import annotations

import argparse
import json
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS


def create_app(status_file: Path) -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/status")
    def status():
        if not status_file.exists():
            return jsonify({"status": "idle", "message": "No monitoring output yet."})
        with status_file.open("r", encoding="utf-8") as handle:
            return jsonify(json.load(handle))

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
