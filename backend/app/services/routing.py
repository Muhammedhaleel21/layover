"""Routing and distance calculation services."""

import math
import asyncio
import httpx
from typing import Optional
from ..config import config
from .cache import cache


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate haversine distance between two points in kilometers."""
    # Convert latitude and longitude from degrees to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    earth_radius_km = 6371.0
    return earth_radius_km * c


class RoutingService:
    """Service for calculating travel times and distances."""
    
    def __init__(self):
        self.osrm_url = config.OSRM_URL
    
    def get_travel_speed(self, mode: str) -> float:
        """Get travel speed in km/h based on mode."""
        speeds = {
            "walk": config.WALK_SPEED,
            "transit": config.TRANSIT_SPEED,
            "both": config.COMBINED_SPEED
        }
        return speeds.get(mode, config.COMBINED_SPEED)
    
    async def calculate_travel_time(
        self, 
        from_lat: float, 
        from_lng: float, 
        to_lat: float, 
        to_lng: float, 
        mode: str
    ) -> int:
        """
        Calculate travel time in minutes between two points.
        Uses OSRM if available, otherwise haversine distance with detour factor.
        """
        cache_key = f"travel:{from_lat}:{from_lng}:{to_lat}:{to_lng}:{mode}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Try OSRM if URL is configured and mode supports it
        if self.osrm_url and mode in ["walk", "both"]:
            osrm_time = await self._get_osrm_time(from_lat, from_lng, to_lat, to_lng, mode)
            if osrm_time is not None:
                cache.set(cache_key, osrm_time, config.CACHE_TTL)
                return osrm_time
        
        # Fall back to haversine distance with detour factor
        distance_km = haversine_distance(from_lat, from_lng, to_lat, to_lng)
        detoured_distance = distance_km * config.DETOUR_FACTOR
        speed_kmh = self.get_travel_speed(mode)
        time_hours = detoured_distance / speed_kmh
        time_minutes = int(time_hours * 60)
        
        cache.set(cache_key, time_minutes, config.CACHE_TTL)
        return time_minutes
    
    async def _get_osrm_time(
        self, 
        from_lat: float, 
        from_lng: float, 
        to_lat: float, 
        to_lng: float, 
        mode: str
    ) -> Optional[int]:
        """Get travel time from OSRM routing service."""
        if not self.osrm_url:
            return None
        
        # Use walking profile for walk mode, driving for others
        profile = "walking" if mode == "walk" else "driving"
        
        url = f"{self.osrm_url}/route/v1/{profile}/{from_lng},{from_lat};{to_lng},{to_lat}"
        params = {
            "overview": "false",
            "alternatives": "false",
            "steps": "false"
        }
        
        try:
            async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    duration_seconds = data["routes"][0]["duration"]
                    return int(duration_seconds / 60)  # Convert to minutes
                
        except (httpx.RequestError, httpx.HTTPStatusError, KeyError, ValueError):
            pass  # Fall back to haversine
        
        return None
    
    def estimate_visit_time(self, categories: list[str]) -> int:
        """Estimate visit time in minutes based on place categories."""
        visit_times = {
            "history": 45,    # Museums, monuments
            "food": 30,       # Cafes, restaurants  
            "culture": 40,    # Galleries, theaters
            "nature": 35,     # Parks, beaches
            "mixed": 35       # Default
        }
        
        # Use the maximum time for places with multiple categories
        if not categories:
            return visit_times["mixed"]
        
        max_time = max(visit_times.get(cat, visit_times["mixed"]) for cat in categories)
        return max_time
    
    def estimate_cost(self, categories: list[str]) -> int:
        """Estimate cost in INR based on place categories."""
        base_costs = {
            "history": 50,    # Museum entry, guide tips
            "food": 120,      # Meal or snacks
            "culture": 60,    # Gallery entry, show tickets
            "nature": 30,     # Minimal cost for parks
            "mixed": 50       # Default
        }
        
        # Use the maximum cost for places with multiple categories
        if not categories:
            return base_costs["mixed"]
        
        max_cost = max(base_costs.get(cat, base_costs["mixed"]) for cat in categories)
        return max_cost


routing_service = RoutingService()