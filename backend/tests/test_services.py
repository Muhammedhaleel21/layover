"""Tests for service modules."""

import pytest
import respx
import httpx
from unittest.mock import AsyncMock, patch

from app.services.places import places_service
from app.services.geocode import geocoding_service
from app.services.routing import routing_service, haversine_distance
from app.services.timecalc import calculate_usable_minutes, time_fits_with_buffer
from app.services.fallback import get_fallback_places, get_fallback_mission_data
from datetime import datetime, timedelta


class TestPlacesService:
    """Tests for places service."""
    
    @pytest.mark.asyncio
    async def test_overpass_success(self):
        """Test successful Overpass API call."""
        mock_response = {
            "elements": [
                {
                    "type": "node",
                    "id": 123,
                    "lat": 11.2588,
                    "lon": 75.7804,
                    "tags": {
                        "name": "Test Park",
                        "leisure": "park",
                        "opening_hours": "24/7"
                    }
                }
            ]
        }
        
        with respx.mock:
            respx.post("https://overpass-api.de/api/interpreter").mock(
                return_value=httpx.Response(200, json=mock_response)
            )
            
            places = await places_service.fetch_places(11.25, 75.78, 120, "walk", "nature")
            
            assert len(places) == 1
            assert places[0].name == "Test Park"
            assert places[0].lat == 11.2588
            assert places[0].lng == 75.7804
            assert "nature" in places[0].categories
    
    @pytest.mark.asyncio 
    async def test_overpass_failure(self):
        """Test Overpass API failure handling."""
        with respx.mock:
            respx.post("https://overpass-api.de/api/interpreter").mock(
                return_value=httpx.Response(500)
            )
            
            places = await places_service.fetch_places(11.25, 75.78, 120, "walk", "nature")
            assert places == []
    
    def test_opening_hours_parsing(self):
        """Test opening hours parsing."""
        assert places_service._parse_opening_hours("24/7") == "open"
        assert places_service._parse_opening_hours("Mo-Fr 09:00-18:00") == "unknown"
        assert places_service._parse_opening_hours("closed") == "closed"
        assert places_service._parse_opening_hours("") == "unknown"
    
    def test_categorization(self):
        """Test place categorization."""
        tags1 = {"historic": "monument", "name": "Test Monument"}
        categories1 = places_service._categorize_place(tags1)
        assert "history" in categories1
        
        tags2 = {"amenity": "cafe", "name": "Test Cafe"}
        categories2 = places_service._categorize_place(tags2)
        assert "food" in categories2
        
        tags3 = {"leisure": "park", "name": "Test Park"}
        categories3 = places_service._categorize_place(tags3)
        assert "nature" in categories3


class TestGeocodingService:
    """Tests for geocoding service."""
    
    @pytest.mark.asyncio
    async def test_geocode_success(self):
        """Test successful geocoding."""
        mock_response = [{
            "lat": "11.2476",
            "lon": "75.7836",
            "display_name": "Kozhikode Railway Station"
        }]
        
        with respx.mock:
            respx.get("https://nominatim.openstreetmap.org/search").mock(
                return_value=httpx.Response(200, json=mock_response)
            )
            
            result = await geocoding_service.geocode("Kozhikode Station")
            assert result is not None
            
            name, lat, lng = result
            assert lat == 11.2476
            assert lng == 75.7836
            assert "Kozhikode" in name
    
    @pytest.mark.asyncio
    async def test_geocode_failure(self):
        """Test geocoding failure."""
        with respx.mock:
            respx.get("https://nominatim.openstreetmap.org/search").mock(
                return_value=httpx.Response(200, json=[])
            )
            
            result = await geocoding_service.geocode("nonexistent location")
            assert result is None


class TestRoutingService:
    """Tests for routing service."""
    
    def test_haversine_distance(self):
        """Test haversine distance calculation."""
        # Distance from Kozhikode station to Mananchira Square (approximately)
        dist = haversine_distance(11.2476, 75.7836, 11.2588, 75.7804)
        assert 1.0 < dist < 2.0  # Should be around 1.4 km
    
    @pytest.mark.asyncio
    async def test_travel_time_calculation(self):
        """Test travel time calculation."""
        time_min = await routing_service.calculate_travel_time(
            11.2476, 75.7836,  # Start
            11.2588, 75.7804,  # End  
            "walk"
        )
        assert time_min > 0
        assert time_min < 60  # Should be reasonable for short distance
    
    def test_visit_time_estimation(self):
        """Test visit time estimation."""
        assert routing_service.estimate_visit_time(["history"]) == 45
        assert routing_service.estimate_visit_time(["food"]) == 30
        assert routing_service.estimate_visit_time(["culture"]) == 40
        assert routing_service.estimate_visit_time(["nature"]) == 35
        assert routing_service.estimate_visit_time([]) == 35
    
    def test_cost_estimation(self):
        """Test cost estimation.""" 
        assert routing_service.estimate_cost(["history"]) == 50
        assert routing_service.estimate_cost(["food"]) == 120
        assert routing_service.estimate_cost(["culture"]) == 60
        assert routing_service.estimate_cost(["nature"]) == 30
        assert routing_service.estimate_cost([]) == 50


class TestTimeCalc:
    """Tests for time calculation utilities."""
    
    def test_calculate_usable_minutes(self):
        """Test usable minutes calculation."""
        # Test direct minutes
        assert calculate_usable_minutes(180) == 180
        
        # Test delay minutes (should override)
        assert calculate_usable_minutes(180, delay_minutes=60) == 60
        
        # Test scheduled departure (future)
        future = datetime.now() + timedelta(minutes=120)
        result = calculate_usable_minutes(180, scheduled_departure=future)
        assert 115 <= result <= 125  # Allow some variance for test timing
        
        # Test scheduled departure (past)
        past = datetime.now() - timedelta(minutes=30)
        assert calculate_usable_minutes(180, scheduled_departure=past) == 0
    
    def test_time_fits_with_buffer(self):
        """Test time fitting calculation with buffer."""
        # Should fit
        assert time_fits_with_buffer(
            current_time=30, travel_min=20, visit_min=30, 
            return_min=20, buffer_min=30, total_available=180
        ) == True
        
        # Should not fit
        assert time_fits_with_buffer(
            current_time=100, travel_min=30, visit_min=30,
            return_min=30, buffer_min=30, total_available=180  
        ) == False


class TestFallback:
    """Tests for fallback data."""
    
    def test_get_fallback_places(self):
        """Test fallback places retrieval."""
        places = get_fallback_places()
        assert len(places) >= 3
        assert all(place.name for place in places)
        assert all(place.lat and place.lng for place in places)
    
    def test_get_fallback_mission_data(self):
        """Test fallback mission data."""
        data = get_fallback_mission_data("mananchira")
        assert "title" in data
        assert "riddle" in data
        assert "hints" in data
        assert "answers" in data
        
        # Test unknown ID
        unknown_data = get_fallback_mission_data("unknown_place")
        assert "title" in unknown_data  # Should return default template