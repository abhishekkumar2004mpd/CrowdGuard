# crowdGuard

`crowdGuard` is a deployment-oriented crowd monitoring backend built on YOLOv8 for client installations. It is designed to count people from webcams, CCTV IP streams, RTSP feeds, HTTP/MJPEG streams, video files, and operating-system-exposed wireless cameras, then estimate crowd risk against area size and safe occupancy rules.

## Core capabilities

- YOLOv8 person detection for real-time crowd counting
- Camera source abstraction for webcam, RTSP/IP CCTV, HTTP streams, files, and paired wireless devices
- Area-aware risk engine with warning and critical stampede alerts
- Separate CSV logs for warning and critical incidents
- Optional Google Maps-assisted area metadata workflow
- Frontend-ready JSON summaries and clean package structure

## Project layout

- `app.py`: application entry point
- `api.py`: lightweight API server for future frontend integration
- `bootstrap_env.ps1`: creates a virtual environment and installs dependencies
- `config/crowdguard.sample.json`: deployment configuration template
- `crowdguard/`: core Python package
- `logs/`: generated metrics and alert CSV files

## Quick start

```powershell
cd crowdGuard
.\bootstrap_env.ps1
copy .env.example .env
copy config\crowdguard.sample.json config\crowdguard.local.json
.\.venv\Scripts\python.exe app.py --config config\crowdguard.local.json
.\.venv\Scripts\python.exe api.py
```

## Google Maps support

If you want address-based area metadata or Google Places lookups, add a `GOOGLE_MAPS_API_KEY` in `.env` and enable the related config block. This requires you to create a Google Cloud API key and enable the Maps/Geocoding services you plan to use.

Without an API key, `crowdGuard` still works using manually configured area dimensions or directly supplied map polygons.

## Deployment note

Bluetooth and other wireless cameras are supported when the device is exposed to Windows as:

- a webcam index like `0`, `1`, `2`
- a stream URL such as `rtsp://...` or `http://...`
- a bridge/virtual-camera source created by the camera vendor app

Direct low-level Bluetooth video transport is hardware-vendor-specific, so the deployment path is to pair the device with Windows and then configure the resulting index or URL.
