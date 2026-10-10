import logging
from typing import List, Dict, Any, Tuple
import httpx
from app.config import settings
from app.services.haversine import haversine_matrix, haversine_travel_time_seconds

logger = logging.getLogger(__name__)


async def get_travel_time_matrix(locations: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    Get travel time matrix from OSRM table service.
    Falls back to haversine * 1.3 at 30 km/h on failure or timeout.
    locations: list of dicts with 'latitude' and 'longitude'
    Returns: {"matrix": [[...], ...], "estimated": bool}
    """
    n = len(locations)
    if n <= 1:
        return {"matrix": [[0.0] * n for _ in range(n)], "estimated": False}

    # Format for OSRM: longitude,latitude;longitude,latitude...
    coords_str = ";".join(f"{loc['longitude']},{loc['latitude']}" for loc in locations)
    url = f"{settings.OSRM_URL}/table/v1/driving/{coords_str}?annotations=duration"

    try:
        async with httpx.AsyncClient(timeout=settings.OSRM_TIMEOUT) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok" and "durations" in data:
                    durations = data["durations"]
                    # Verify no None values in matrix
                    has_none = any(val is None for row in durations for val in row)
                    if not has_none:
                        return {"matrix": durations, "estimated": False}
    except Exception as exc:
        logger.warning("OSRM unavailable (%s), using haversine fallback", exc)

    # Fallback to haversine matrix
    fallback = haversine_matrix(
        locations,
        road_factor=settings.FALLBACK_ROAD_FACTOR,
        speed_kmh=settings.FALLBACK_SPEED_KMH,
    )
    return {"matrix": fallback, "estimated": True}


async def get_travel_time_between(
    loc1: Dict[str, float], loc2: Dict[str, float]
) -> Tuple[int, bool]:
    """Calculates travel time in seconds between two points using OSRM with haversine fallback."""
    res = await get_travel_time_matrix([loc1, loc2])
    matrix = res["matrix"]
    estimated = res["estimated"]
    return int(round(matrix[0][1])), estimated
