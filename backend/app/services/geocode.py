"""Geocoding service using Nominatim API."""

import asyncio
import httpx
from typing import Optional, Tuple
from ..config import config
from .cache import cache


class GeocodingService:
    """Service for geocoding addresses using Nominatim."""
    
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org"
        self.headers = {
            "User-Agent": "LAYOVER/1.0 (Hackathon Project)"
        }
    
    async def geocode(self, query: str) -> Optional[Tuple[str, float, float]]:
        """
        Geocode a location string to name, lat, lng.
        Returns None if geocoding fails.
        """
        cache_key = f"geocode:{query.lower()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        params = {
            "q": query,
            "format": "json",
            "limit": "1",
            "addressdetails": "1"
        }
        
        for attempt in range(2):  # One retry
            try:
                async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
                    response = await client.get(
                        f"{self.base_url}/search",
                        params=params,
                        headers=self.headers
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    if not data:
                        cache.set(cache_key, None, config.CACHE_TTL)
                        return None
                    
                    result = data[0]
                    name = result.get("display_name", query)
                    lat = float(result["lat"])
                    lng = float(result["lon"])
                    
                    result_tuple = (name, lat, lng)
                    cache.set(cache_key, result_tuple, config.CACHE_TTL)
                    return result_tuple
                    
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError) as e:
                if attempt == 0:
                    await asyncio.sleep(1)  # Brief delay before retry
                    continue
                # Cache negative result briefly to avoid hammering the API
                cache.set(cache_key, None, 300)  # 5 minutes
                return None
        
        return None


geocoding_service = GeocodingService()