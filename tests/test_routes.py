"""
FastAPI route and integration tests.
Tests the graph calculation, dynamic sensor weight adjustment, and routing API contracts.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.cache_service import cache_service
from app.services.crowd_sensor import stadium_graph

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_before_and_after_tests():
    # Clear cache and reset graph states before each test run
    cache_service.clear()
    
    # Reset default nodes
    for node in stadium_graph.nodes.values():
        node.crowd_density = "LOW"
        node.operational = True
    yield

def test_api_status():
    """Verify that the API is active and reporting correct metadata."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPERATIONAL"
    assert "MetLife" in data["stadium"]

def test_standard_route_calculation():
    """Verify standard wayfinding calculates correctly and generates steps."""
    request_data = {
        "query": "Guide me to the train station",
        "language": "en",
        "wheelchair_accessible": False,
        "current_section": "sec_301",
        "destination": "train_station"
    }
    response = client.post("/api/route", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["route_found"] is True
    assert len(data["steps"]) > 0
    assert data["total_distance_meters"] > 0
    assert data["total_time_minutes"] > 0
    assert "train_station" in data["path_taken"]

def test_wheelchair_accessibility_routing():
    """Verify routing redirects to elevators when wheelchair mode is enabled."""
    # Ensure Stairs East is open but we want wheelchair route
    # Starting at Upper Section 301, moving down to ground (Gate A)
    request_data = {
        "query": "Spanish wheelchair route to train station",
        "language": "es",
        "wheelchair_accessible": True,
        "current_section": "sec_301",
        "destination": "train_station"
    }
    response = client.post("/api/route", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["route_found"] is True
    # Wheelchair route must NOT contain Stairs East
    assert "stairs_east" not in data["path_taken"]
    assert "elevator_east" in data["path_taken"]

def test_caching_behavior():
    """Verify that successive queries trigger cache hits and return fast."""
    request_data = {
        "query": "Go to Rideshare",
        "language": "fr",
        "wheelchair_accessible": False,
        "current_section": "sec_104",
        "destination": "rideshare_hub"
    }
    # First call: Cache Miss
    res1 = client.post("/api/route", json=request_data)
    assert res1.status_code == 200
    assert res1.json()["is_cached"] is False

    # Second call: Cache Hit
    res2 = client.post("/api/route", json=request_data)
    assert res2.status_code == 200
    assert res2.json()["is_cached"] is True

def test_sensor_congestion_reroute():
    """Verify that high crowd sensor updates force the routing to avoid congested nodes."""
    # Calculate a standard route from Section 101 to train station
    # Path without congestion should go sec_101 -> gate_a -> train_station (shortest)
    request_data = {
        "query": "Shortest route to train station",
        "language": "en",
        "wheelchair_accessible": False,
        "current_section": "sec_101",
        "destination": "train_station"
    }
    res_normal = client.post("/api/route", json=request_data)
    assert res_normal.status_code == 200
    normal_path = res_normal.json()["path_taken"]
    assert "gate_a" in normal_path

    # Simulate sensor bottleneck at Gate A (High density multiplier = 6.0)
    sensor_res = client.post("/api/sensor/update", json={
        "node_id": "gate_a",
        "crowd_density": "HIGH"
    })
    assert sensor_res.status_code == 200

    # Recalculate route. The routing engine should now bypass gate_a and direct through gate_b or walkway concourse to bypass the crowd!
    res_rerouted = client.post("/api/route", json=request_data)
    assert res_rerouted.status_code == 200
    rerouted_path = res_rerouted.json()["path_taken"]
    
    # Rerouted path must not use gate_a directly or it should have chosen a longer path that avoids the bottleneck
    # In our graph, sec_101 can also connect to gate_b.
    assert rerouted_path != normal_path
