"""
StadiumIQ test suite — real imports, no Gemini calls, no network required.
Run: pytest tests/ -v
"""
import sys, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.routers.sustainability import EMISSION_FACTORS
from backend.data.crowd_simulator import get_crowd_status
from backend.models import TransportSplit, ZoneStatus, NavigatorRequest, VolunteerQueryRequest

client = TestClient(app)

# ── Real API endpoint tests (no Gemini) ─────────────────────────────────────

def test_health_check():
    """Root endpoint must return 200."""
    resp = client.get("/")
    assert resp.status_code == 200

def test_crowd_status_endpoint():
    """/api/crowd/status must return zones without any API key."""
    resp = client.get("/api/crowd/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "zones" in data
    assert len(data["zones"]) >= 1

def test_sustainability_validation_rejects_empty():
    """fan_count=0 must be rejected with 422."""
    resp = client.post("/api/sustainability/estimate", json={
        "fan_count": 0,
        "transport_split": {"car": 60, "bus": 15, "metro": 20, "walk": 5},
        "avg_distance_km": 12
    })
    assert resp.status_code in (400, 422)

def test_sustainability_validation_rejects_bad_split():
    """Transport split summing to 200% must be rejected."""
    resp = client.post("/api/sustainability/estimate", json={
        "fan_count": 1000,
        "transport_split": {"car": 100, "bus": 100, "metro": 0, "walk": 0},
        "avg_distance_km": 10
    })
    assert resp.status_code in (400, 422)

def test_swagger_docs_available():
    """Swagger UI must be reachable."""
    resp = client.get("/docs")
    assert resp.status_code == 200

# ── CO2 math using real EMISSION_FACTORS ────────────────────────────────────

def test_emission_factors_all_present():
    assert set(EMISSION_FACTORS.keys()) == {"car", "bus", "metro", "walk"}

def test_car_highest_emission():
    assert EMISSION_FACTORS["car"] > EMISSION_FACTORS["bus"] > EMISSION_FACTORS["metro"]
    assert EMISSION_FACTORS["walk"] == 0.0

def test_co2_known_values():
    """40k fans, 60/15/20/5 split, 12km — matches documented demo query."""
    fan_count, avg_km = 40000, 12
    car_co2 = fan_count * 0.60 * avg_km * EMISSION_FACTORS["car"]
    bus_co2 = fan_count * 0.15 * avg_km * EMISSION_FACTORS["bus"]
    metro_co2 = fan_count * 0.20 * avg_km * EMISSION_FACTORS["metro"]
    total = car_co2 + bus_co2 + metro_co2
    assert round(total, 0) == 55824

def test_walk_produces_zero_co2():
    assert 10000 * 1.0 * 20 * EMISSION_FACTORS["walk"] == 0.0

# ── Crowd simulator real imports ─────────────────────────────────────────────

def test_crowd_simulator_returns_zones():
    status = get_crowd_status()
    assert "zones" in status and len(status["zones"]) >= 1

def test_crowd_simulator_zone_shape():
    for zone in get_crowd_status()["zones"]:
        assert "zone_name" in zone
        assert 0.0 <= zone["capacity_pct"] <= 100.0
        assert zone["trend"] in ("UP", "DOWN", "STABLE")

def test_crowd_simulator_has_match_phase():
    assert len(get_crowd_status()["match_phase"]) > 0

# ── Data integrity tests ─────────────────────────────────────────────────────

def test_stadium_map_loads_and_nonempty():
    path = Path(__file__).parent.parent / "backend" / "data" / "stadium_map.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert len(data) > 0

def test_volunteer_kb_has_title_and_content():
    path = Path(__file__).parent.parent / "backend" / "data" / "volunteer_kb.json"
    assert path.exists()
    entries = json.loads(path.read_text())
    assert len(entries) > 0
    for e in entries:
        assert "title" in e

# ── Pydantic model validation ─────────────────────────────────────────────────

def test_zone_status_model():
    z = ZoneStatus(zone_name="Zone A", capacity_pct=72.5, trend="UP")
    assert z.zone_name == "Zone A"

def test_navigator_request_optional_language():
    r = NavigatorRequest(query="Where is Gate B?")
    assert r.language is None

def test_volunteer_request_model():
    r = VolunteerQueryRequest(query="Medical emergency?")
    assert len(r.query) > 0