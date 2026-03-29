from __future__ import annotations

import math
import os
from typing import Any

import requests


def polygon_area_sq_meters(points: list[list[float]]) -> float:
    if len(points) < 3:
        return 0.0

    earth_radius = 6378137.0
    projected = []
    for lat, lng in points:
        x = math.radians(lng) * earth_radius * math.cos(math.radians(lat))
        y = math.radians(lat) * earth_radius
        projected.append((x, y))

    area = 0.0
    for index in range(len(projected)):
        x1, y1 = projected[index]
        x2, y2 = projected[(index + 1) % len(projected)]
        area += (x1 * y2) - (x2 * y1)
    return abs(area) / 2.0


def resolve_google_place_metadata(config: dict[str, Any]) -> dict[str, Any]:
    enabled = bool(config.get("enabled"))
    place_id = config.get("place_id")
    location_name = config.get("location_name")
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()

    if not enabled:
        return {"enabled": False, "message": "Google Maps integration disabled."}

    if config.get("polygon"):
        area = polygon_area_sq_meters(config["polygon"])
        return {"enabled": True, "source": "polygon", "area_sq_meters": area}

    if not api_key:
        return {
            "enabled": True,
            "source": "missing_api_key",
            "message": "Set GOOGLE_MAPS_API_KEY in .env to use Google Maps lookups.",
        }

    if place_id:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        response = requests.get(
            url,
            params={"place_id": place_id, "fields": "name,geometry", "key": api_key},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return {"enabled": True, "source": "google_place_details", "raw": data}

    if location_name:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        response = requests.get(
            url,
            params={"address": location_name, "key": api_key},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return {"enabled": True, "source": "google_geocode", "raw": data}

    return {"enabled": True, "source": "incomplete", "message": "Provide place_id, location_name, or polygon."}
