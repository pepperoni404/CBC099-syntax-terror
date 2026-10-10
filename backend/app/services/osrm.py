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


async def get_route_geometry(coordinates: Any) -> Dict[str, Any]:
    """
    Get driving route geometry from OSRM route service.
    Coordinates can be:
      - Semicolon-separated lon,lat pairs: "lon1,lat1;lon2,lat2;..."
      - List of dicts with 'latitude' and 'longitude'
      - List of [lat, lng] pairs
    Returns:
      {"geometry": [[lat, lng], ...], "estimated": bool, "distance": float, "duration": float}
    Falls back to straight lines connecting waypoints on OSRM failure or timeout (3s).
    """
    fallback_geometry: List[List[float]] = []
    valid_pairs: List[str] = []

    if isinstance(coordinates, str):
        coords_str = coordinates.strip()
        if not coords_str:
            return {"geometry": [], "estimated": False, "distance": 0.0, "duration": 0.0}
        for p in coords_str.split(";"):
            p = p.strip()
            if not p:
                continue
            try:
                parts = p.split(",")
                lon = float(parts[0].strip())
                lat = float(parts[1].strip())
                fallback_geometry.append([lat, lon])
                valid_pairs.append(f"{lon},{lat}")
            except (ValueError, IndexError):
                continue
    elif isinstance(coordinates, list):
        for item in coordinates:
            if isinstance(item, dict):
                lat = float(item.get("latitude", item.get("lat", 0.0)))
                lon = float(item.get("longitude", item.get("lng", 0.0)))
                fallback_geometry.append([lat, lon])
                valid_pairs.append(f"{lon},{lat}")
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                lat = float(item[0])
                lon = float(item[1])
                fallback_geometry.append([lat, lon])
                valid_pairs.append(f"{lon},{lat}")

    if len(fallback_geometry) <= 1:
        return {"geometry": fallback_geometry, "estimated": False, "distance": 0.0, "duration": 0.0}

    osrm_coords_str = ";".join(valid_pairs)
    url = f"{settings.OSRM_URL}/route/v1/driving/{osrm_coords_str}?overview=full&geometries=geojson"

    try:
        async with httpx.AsyncClient(timeout=settings.OSRM_TIMEOUT) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok" and "routes" in data and len(data["routes"]) > 0:
                    route = data["routes"][0]
                    geojson_coords = route.get("geometry", {}).get("coordinates", [])
                    if geojson_coords:
                        # GeoJSON coordinates are [longitude, latitude] -> convert to [lat, lng] for Leaflet
                        leaflet_geometry = [[float(pt[1]), float(pt[0])] for pt in geojson_coords]
                        return {
                            "geometry": leaflet_geometry,
                            "estimated": False,
                            "distance": float(route.get("distance", 0.0)),
                            "duration": float(route.get("duration", 0.0)),
                        }
    except Exception as exc:
        logger.warning("OSRM route service unavailable (%s), using straight-line fallback", exc)

    return {
        "geometry": fallback_geometry,
        "estimated": True,
        "distance": 0.0,
        "duration": 0.0,
    }


get_route = get_route_geometry

