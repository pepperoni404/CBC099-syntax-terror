import math
from typing import List, Dict
from app.config import settings


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in meters using Haversine formula."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def haversine_travel_time_seconds(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    road_factor: float = settings.FALLBACK_ROAD_FACTOR,
    speed_kmh: float = settings.FALLBACK_SPEED_KMH,
) -> int:
    """Calculates travel time in seconds: haversine * road_factor at speed_kmh."""
    dist_m = haversine_distance_meters(lat1, lon1, lat2, lon2)
    road_dist_km = (dist_m / 1000.0) * road_factor
    hours = road_dist_km / speed_kmh
    return int(round(hours * 3600.0))


def haversine_matrix(
    locations: List[Dict[str, float]],
    road_factor: float = settings.FALLBACK_ROAD_FACTOR,
    speed_kmh: float = settings.FALLBACK_SPEED_KMH,
) -> List[List[float]]:
    """Calculates NxN travel duration matrix in seconds for given locations."""
    n = len(locations)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = float(
                    haversine_travel_time_seconds(
                        locations[i]["latitude"],
                        locations[i]["longitude"],
                        locations[j]["latitude"],
                        locations[j]["longitude"],
                        road_factor=road_factor,
                        speed_kmh=speed_kmh,
                    )
                )
    return matrix
