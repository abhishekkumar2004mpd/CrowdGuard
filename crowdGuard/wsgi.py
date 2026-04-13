from pathlib import Path

from crowdguard.api import create_app


app = create_app(
    Path(__file__).resolve().parent / "logs" / "latest_status.json",
    Path(__file__).resolve().parent / "config" / "crowdguard.sample.json",
)
