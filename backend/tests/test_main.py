"""Tests for the main FastAPI application."""

import pytest
import respx
import httpx
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.schemas import AdventureRequest


client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    with patch('app.services.places.places_service.health_check', return_value=True):
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert "llm_configured" in data
        assert "places_source_reachable" in data


def test_geocode_success():
    """Test geocoding endpoint with successful result."""
    mock_response = {
        "lat": "11.2476",
        "lon": "75.7836", 
        "display_name": "Kozhikode Railway Station, Kerala, India"
    }
    
    with respx.mock:
        respx.get("https://nominatim.openstreetmap.org/search").mock(
            return_value=httpx.Response(200, json=[mock_response])
        )
        
        response = client.get("/api/geocode?q=Kozhikode Railway Station")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Kozhikode Railway Station, Kerala, India"
        assert data["lat"] == 11.2476
        assert data["lng"] == 75.7836


def test_geocode_not_found():
    """Test geocoding endpoint with no results."""
    with respx.mock:
        respx.get("https://nominatim.openstreetmap.org/search").mock(
            return_value=httpx.Response(200, json=[])
        )
        
        response = client.get("/api/geocode?q=nonexistent place")
        assert response.status_code == 404


def test_create_adventure_fallback():
    """Test creating adventure with fallback data."""
    request_data = {
        "start": "Kozhikode",
        "minutes": 180,
        "budget": 500,
        "buffer": 30,
        "mode": "both",
        "style": "mixed", 
        "difficulty": "medium"
    }
    
    # Mock empty Overpass response to trigger fallback
    with respx.mock:
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(200, json={"elements": []})
        )
        
        response = client.post("/api/adventures", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["source"] == "fallback"
        assert "id" in data
        assert "missions" in data
        assert isinstance(data["missions"], list)


def test_tiny_budget():
    """Test adventure with very small budget."""
    request_data = {
        "start": "Kozhikode",
        "minutes": 60,
        "budget": 10,  # Very small budget
        "buffer": 30,
        "mode": "walk",
        "style": "nature",
        "difficulty": "easy"
    }
    
    with respx.mock:
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(200, json={"elements": []})
        )
        
        response = client.post("/api/adventures", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        # Should still return valid response, possibly with warnings
        assert "missions" in data
        if not data["missions"]:
            assert len(data["warnings"]) > 0


def test_tiny_time():
    """Test adventure with very little time."""
    request_data = {
        "start": "Kozhikode", 
        "minutes": 35,  # Just barely above minimum
        "budget": 500,
        "buffer": 30,  # Most of the time is buffer
        "mode": "walk", 
        "style": "mixed",
        "difficulty": "easy"
    }
    
    with respx.mock:
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(200, json={"elements": []})
        )
        
        response = client.post("/api/adventures", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        # May have no missions due to time constraints 
        assert "missions" in data


def test_get_adventure_not_found():
    """Test getting non-existent adventure."""
    response = client.get("/api/adventures/nonexistent")
    assert response.status_code == 404


def test_answer_check():
    """Test answer checking functionality."""
    # First create an adventure
    request_data = {
        "start": "Kozhikode",
        "minutes": 180,
        "budget": 500,
        "buffer": 30,
        "mode": "both",
        "style": "mixed",
        "difficulty": "medium"
    }
    
    with respx.mock:
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(200, json={"elements": []})
        )
        
        create_response = client.post("/api/adventures", json=request_data)
        adventure_id = create_response.json()["id"]
        
        # Test correct answer
        answer_data = {
            "mission_id": "mananchira",
            "answer": "Mananchira Square"
        }
        
        response = client.post(f"/api/adventures/{adventure_id}/answer", json=answer_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "correct" in data


def test_invalid_request_validation():
    """Test request validation."""
    invalid_data = {
        "start": "",  # Empty start
        "minutes": 10,  # Too few minutes  
        "budget": -100,  # Negative budget
        "buffer": 5,  # Too small buffer
        "mode": "invalid",  # Invalid mode
        "style": "invalid",  # Invalid style
        "difficulty": "invalid"  # Invalid difficulty
    }
    
    response = client.post("/api/adventures", json=invalid_data)
    assert response.status_code == 422  # Validation error