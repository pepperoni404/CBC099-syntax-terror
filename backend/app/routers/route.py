import logging
from typing import List, Union
from fastapi import APIRouter, Query
from app.services.osrm import get_route_geometry
from app.schemas import RouteResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["route"])


@router.get("/route", response_model=Union[List[List[float]], RouteResponse])
async def get_route(
    coordinates: str = Query(..., description="semicolon-separated lon,lat pairs"),
    format: str = Query(None, description="Optional format: 'object' or 'array'"),
):
    """
    Returns driving route geometry as an array of [lat, lng] pairs (Leaflet format).
    Calls OSRM /route/v1/driving/{coordinates}?overview=full&geometries=geojson
    Falls back to straight-line coordinates if OSRM is unavailable or times out.
    """
    res = await get_route_geometry(coordinates)
    if format == "object":
        return RouteResponse(
            geometry=res["geometry"],
            distance=res.get("distance", 0.0),
            duration=res.get("duration", 0.0),
            estimated=res.get("estimated", False),
        )
    return res["geometry"]
