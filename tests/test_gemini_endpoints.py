"""
Additional coverage for the 4 Gemini-calling endpoints, using mocks so no
real API key or network call is needed. Does not modify test_stadiumiq.py.
Run: pytest tests/ -v
"""
import sys, json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from backend.main import app
from backend import gemini_client

client = TestClient(app)


def _mock_response(payload: dict):
    """Build a fake Gemini response object with the given JSON payload."""
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(payload)
    return mock_resp


# ── Navigator ────────────────────────────────────────────────────────────

def test_navigate_empty_query_rejected():
    resp = client.post("/api/navigate", json={"query": "   "})
    assert resp.status_code == 400


def test_navigate_returns_grounded_answer():
    fake = _mock_response({"answer": "Gate B is near you.", "detected_language": "English"})
    with patch.object(gemini_client.model, "generate_content", return_value=fake):
        resp = client.post("/api/navigate", json={"query": "Where is Gate B?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "Gate B is near you."
    assert data["detected_language"] == "English"


def test_navigate_falls_back_on_gemini_error():
    with patch.object(gemini_client.model, "generate_content", side_effect=RuntimeError("boom")):
        resp = client.post("/api/navigate", json={"query": "Where is Gate B?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Error communicating with Gemini" in data["answer"]


# ── Crowd alerts ─────────────────────────────────────────────────────────

def test_crowd_alert_empty_zones_rejected():
    resp = client.post("/api/crowd/alert", json={"zones": []})
    assert resp.status_code == 400


def test_crowd_alert_uses_adjacency_in_prompt():
    fake = _mock_response({"alerts": ["Redirect via Gate D."], "flow_suggestion": "Steady flow."})
    captured = {}

    def capture(prompt, **kwargs):
        captured["prompt"] = prompt
        return fake

    with patch.object(gemini_client.model, "generate_content", side_effect=capture):
        resp = client.post("/api/crowd/alert", json={
            "zones": [{"zone_name": "Zone D", "capacity_pct": 92.0, "trend": "UP"}],
            "match_phase": "Half-time"
        })
    assert resp.status_code == 200
    assert "Gate D (West / VIP & Access)" in captured["prompt"]


def test_crowd_alert_falls_back_on_gemini_error():
    with patch.object(gemini_client.model, "generate_content", side_effect=RuntimeError("boom")):
        resp = client.post("/api/crowd/alert", json={
            "zones": [{"zone_name": "Zone A", "capacity_pct": 50.0, "trend": "STABLE"}]
        })
    assert resp.status_code == 200
    assert resp.json()["alerts"] == ["Error generating crowd intelligence alerts."]


# ── Volunteer assistant ──────────────────────────────────────────────────

def test_volunteer_no_kb_match_skips_gemini_call():
    with patch.object(gemini_client.model, "generate_content") as mock_gen:
        resp = client.post("/api/volunteer/query", json={"query": "asdkjaslkdjaslkdj"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["grounded_on"] == []
    assert "does not seem to match any protocol" in data["answer"]
    mock_gen.assert_not_called()


def test_volunteer_medical_query_grounds_on_matched_protocol():
    fake = _mock_response({"answer": "Call the medical team immediately."})
    with patch.object(gemini_client.model, "generate_content", return_value=fake):
        resp = client.post("/api/volunteer/query", json={"query": "medical emergency section 114"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["grounded_on"]) >= 1
    assert data["answer"] == "Call the medical team immediately."


# ── Sustainability suggestions ──────────────────────────────────────────

def test_sustainability_suggestions_tailored_to_split():
    fake = _mock_response({"suggestions": ["Push carpool rewards for the 60% car share."]})
    with patch.object(gemini_client.model, "generate_content", return_value=fake):
        resp = client.post("/api/sustainability/estimate", json={
            "fan_count": 40000,
            "transport_split": {"car": 60, "bus": 15, "metro": 20, "walk": 5},
            "avg_distance_km": 12
        })
    assert resp.status_code == 200
    assert "carpool" in resp.json()["suggestions"][0].lower()


def test_sustainability_falls_back_on_gemini_error():
    with patch.object(gemini_client.model, "generate_content", side_effect=RuntimeError("boom")):
        resp = client.post("/api/sustainability/estimate", json={
            "fan_count": 1000,
            "transport_split": {"car": 50, "bus": 25, "metro": 20, "walk": 5},
            "avg_distance_km": 10
        })
    assert resp.status_code == 200
    assert resp.json()["suggestions"] == ["Error generating sustainability recommendations."]