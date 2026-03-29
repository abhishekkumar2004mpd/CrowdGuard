# crowdGuard

`crowdGuard` is a deployment-oriented crowd monitoring backend built on YOLOv8 for client installations. It is designed to count people from webcams, CCTV IP streams, RTSP feeds, HTTP/MJPEG streams, video files, and operating-system-exposed wireless cameras, then estimate crowd risk against area size and safe occupancy rules.

## Core capabilities

- YOLOv8 person detection for real-time crowd counting
- YOLOv8 pose validation plus optional tracked line-crossing counting
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

Recommended Google services for this project:

- `Geocoding API` for address-to-location lookup
- `Places API` for place search/details
- `Maps JavaScript API` only if you want an interactive map inside the frontend

## React UI

A React/Vite frontend scaffold is available in [react-ui](C:/Users/KIIT0001/Desktop/Crowd%20control/crowdGuard/react-ui).

Run it with:

```powershell
cd crowdGuard\react-ui
npm.cmd install
npm.cmd run dev
```

This React UI consumes the existing CrowdGuard API at `http://127.0.0.1:5001`.

## Deployment note

Bluetooth and other wireless cameras are supported when the device is exposed to Windows as:

- a webcam index like `0`, `1`, `2`
- a stream URL such as `rtsp://...` or `http://...`
- a bridge/virtual-camera source created by the camera vendor app

Direct low-level Bluetooth video transport is hardware-vendor-specific, so the deployment path is to pair the device with Windows and then configure the resulting index or URL.

## Tracking mode

The sample config now enables tracked people counting inspired by your downloaded scripts:

- persistent YOLO tracking
- optional line-crossing counts for `in` and `out`
- pose-based filtering so the crowd count still prefers real human structure

You can tune the counting line in [crowdguard.sample.json](C:/Users/KIIT0001/Desktop/Crowd%20control/crowdGuard/config/crowdguard.sample.json) by editing the `processing.tracking.line_zone.start_ratio` and `end_ratio` values.

## Display scaling

To enlarge only the user-visible camera window without changing model input or tracking logic, tune these values in [crowdguard.sample.json](C:/Users/KIIT0001/Desktop/Crowd%20control/crowdGuard/config/crowdguard.sample.json):

- `processing.display_scale`
- `processing.display_max_width`
- `processing.display_max_height`

`crowdGuard` draws overlays on the original annotated frame first and resizes only the final display image, so aspect ratio and overlay alignment stay correct.
