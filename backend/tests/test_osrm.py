import pytest
from unittest.mock import patch
import httpx
from app.services.haversine import (
    haversine_distance_meters,
    haversine_travel_time_seconds,
    haversine_matrix,
)
from app.services.osrm import get_travel_time_matrix


def test_haversine_calculations():
    # Distance between two Bangalore locations ~ 2.4 km
    lat1, lon1 = 12.9716, 77.5946
    lat2, lon2 = 12.9800, 77.6100
    dist = haversine_distance_meters(lat1, lon1, lat2, lon2)
    assert 1500 < dist < 3000

    time_sec = haversine_travel_time_seconds(lat1, lon1, lat2, lon2, road_factor=1.3, speed_kmh=30.0)
    assert time_sec > 0

    matrix = haversine_matrix(
        [{"latitude": lat1, "longitude": lon1}, {"latitude": lat2, "longitude": lon2}]
    )
    assert len(matrix) == 2
    assert matrix[0][0] == 0.0
    assert matrix[1][1] == 0.0
    assert matrix[0][1] == matrix[1][0]
    assert matrix[0][1] > 0.0


@pytest.mark.asyncio
async def test_osrm_fallback_on_timeout():
    locations = [
        {"latitude": 12.9716, "longitude": 77.5946},
        {"latitude": 12.9800, "longitude": 77.6100},
    ]

    # Mock timeout exception in httpx
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        res = await get_travel_time_matrix(locations)
        assert res["estimated"] is True
        assert len(res["matrix"]) == 2
        assert res["matrix"][0][1] > 0.0


@pytest.mark.asyncio
async def test_get_route_geometry_fallback_on_timeout():
    coords = "77.5946,12.9716;77.6100,12.9800"
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        from app.services.osrm import get_route_geometry
        res = await get_route_geometry(coords)
        assert res["estimated"] is True
        assert len(res["geometry"]) == 2
        assert res["geometry"][0] == [12.9716, 77.5946]
        assert res["geometry"][1] == [12.9800, 77.6100]


@pytest.mark.asyncio
async def test_get_route_geometry_success():
    coords = "77.5946,12.9716;77.6100,12.9800"
    mock_response = {
        "code": "Ok",
        "routes": [
            {
                "geometry": {
                    "coordinates": [[77.5946, 12.9716], [77.6000, 12.9750], [77.6100, 12.9800]]
                },
                "distance": 2500.0,
                "duration": 300.0,
            }
        ],
    }

    class MockResp:
        status_code = 200
        def json(self):
            return mock_response

    with patch("httpx.AsyncClient.get", return_value=MockResp()):
        from app.services.osrm import get_route_geometry
        res = await get_route_geometry(coords)
        assert res["estimated"] is False
        assert len(res["geometry"]) == 3
        # Converted to [lat, lng]
        assert res["geometry"][0] == [12.9716, 77.5946]
        assert res["geometry"][1] == [12.9750, 77.6000]
        assert res["geometry"][2] == [12.9800, 77.6100]

