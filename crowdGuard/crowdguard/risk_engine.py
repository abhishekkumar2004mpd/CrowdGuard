from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskResult:
    area_sq_meters: float
    safe_capacity: int
    person_count: int
    occupancy_ratio: float
    density: float
    status: str
    message: str


def estimate_area_sq_meters(width_meters: float | None, length_meters: float | None, fallback_area_sq_meters: float) -> float:
    if width_meters and length_meters:
        return width_meters * length_meters
    return fallback_area_sq_meters


def estimate_safe_capacity(area_sq_meters: float, safe_density_per_sq_meter: float) -> int:
    if area_sq_meters <= 0:
        return 0
    return max(int(area_sq_meters * safe_density_per_sq_meter), 1)


def evaluate_risk(
    person_count: int,
    area_sq_meters: float,
    safe_density_per_sq_meter: float,
    warning_threshold: float,
    critical_threshold: float,
) -> RiskResult:
    safe_capacity = estimate_safe_capacity(area_sq_meters, safe_density_per_sq_meter)
    occupancy_ratio = (person_count / safe_capacity) if safe_capacity else 0.0
    density = (person_count / area_sq_meters) if area_sq_meters else 0.0

    if occupancy_ratio >= critical_threshold:
        status = "CRITICAL"
        message = "Stampede happening critical notice. Capacity has crossed the safe limit."
    elif occupancy_ratio >= warning_threshold:
        status = "WARNING"
        message = "Stampede might happen. Crowd is nearing the safe limit."
    else:
        status = "NORMAL"
        message = "Crowd level is currently within the configured safe range."

    return RiskResult(
        area_sq_meters=area_sq_meters,
        safe_capacity=safe_capacity,
        person_count=person_count,
        occupancy_ratio=occupancy_ratio,
        density=density,
        status=status,
        message=message,
    )
