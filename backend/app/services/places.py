"""Places service using OpenStreetMap Overpass API."""

import asyncio
import httpx
import json
from typing import List, Dict, Any, Set
from ..config import config
from ..schemas import Place
from .cache import cache


class PlacesService:
    """Service for fetching places from OpenStreetMap Overpass API."""
    
    def __init__(self):
        self.base_url = "https://overpass-api.de/api/interpreter"
    
    def _get_style_filters(self, style: str) -> str:
        """Get Overpass query filters based on adventure style."""
        filters = {
            "history": '''
                (nwr["historic"~"."]["name"];
                 nwr["tourism"~"^(museum|monument)$"]["name"];)
            ''',
            "food": '''
                (nwr["amenity"~"^(cafe|restaurant|marketplace)$"]["name"];
                 nwr["shop"~"^(confectionery|bakery)$"]["name"];)
            ''',
            "culture": '''
                (nwr["tourism"~"^(gallery|attraction)$"]["name"];
                 nwr["amenity"~"^(arts_centre|theatre|place_of_worship)$"]["name"];)
            ''',
            "nature": '''
                (nwr["leisure"~"^(park|garden)$"]["name"];
                 nwr["natural"="beach"]["name"];)
            ''',
            "mixed": '''
                (nwr["historic"~"."]["name"];
                 nwr["tourism"~"^(museum|monument|gallery|attraction)$"]["name"];
                 nwr["amenity"~"^(cafe|restaurant|marketplace|arts_centre|theatre|place_of_worship)$"]["name"];
                 nwr["shop"~"^(confectionery|bakery)$"]["name"];
                 nwr["leisure"~"^(park|garden)$"]["name"];
                 nwr["natural"="beach"]["name"];)
            '''
        }
        return filters.get(style, filters["mixed"])
    
    def _calculate_radius(self, minutes: int, mode: str) -> float:
        """Calculate search radius in km based on time and travel mode."""
        if mode == "walk":
            speed = config.WALK_SPEED
        elif mode == "transit":
            speed = config.TRANSIT_SPEED
        else:  # both
            speed = config.COMBINED_SPEED
        
        # Convert minutes to hours and account for detour factor
        hours = minutes / 60
        radius_km = hours * speed / config.DETOUR_FACTOR
        
        # Cap radius to reasonable bounds (0.5km to 10km)
        return max(0.5, min(10.0, radius_km))
    
    def _build_query(self, lat: float, lng: float, radius_km: float, style: str) -> str:
        """Build Overpass query."""
        radius_m = int(radius_km * 1000)
        style_filters = self._get_style_filters(style)
        
        query = f'''
        [out:json][timeout:25];
        {style_filters}
        around:{radius_m},{lat},{lng};
        out geom;
        '''
        return query
    
    def _extract_facts(self, tags: Dict[str, str]) -> List[str]:
        """Extract factual information from OSM tags."""
        facts = []
        
        # Add Wikipedia information
        if "wikipedia" in tags:
            facts.append(f"Wikipedia: {tags['wikipedia']}")
        
        # Add description
        if "description" in tags:
            facts.append(f"Description: {tags['description']}")
        
        # Add cuisine information
        if "cuisine" in tags:
            facts.append(f"Cuisine: {tags['cuisine']}")
        
        # Add historical period
        if "historic" in tags and tags["historic"] != "yes":
            facts.append(f"Historic type: {tags['historic']}")
        
        # Add opening hours
        if "opening_hours" in tags:
            facts.append(f"Opening hours: {tags['opening_hours']}")
        
        # Add website
        if "website" in tags:
            facts.append(f"Website: {tags['website']}")
        
        return facts
    
    def _parse_opening_hours(self, opening_hours: str) -> str:
        """
        Simple opening hours parser. Returns 'open', 'closed', or 'unknown'.
        This is a simplified implementation - a full parser would be much more complex.
        """
        if not opening_hours:
            return "unknown"
        
        # Very basic patterns - just catch obvious ones
        opening_hours = opening_hours.lower()
        
        if "24/7" in opening_hours or "always open" in opening_hours:
            return "open"
        
        if "closed" in opening_hours or "off" in opening_hours:
            return "closed"
        
        # For anything else, assume unknown for now
        return "unknown"
    
    def _categorize_place(self, tags: Dict[str, str]) -> List[str]:
        """Categorize a place based on its OSM tags."""
        categories = []
        
        if "historic" in tags:
            categories.append("history")
        
        if tags.get("amenity") in ["cafe", "restaurant", "marketplace"]:
            categories.append("food")
        
        if tags.get("shop") in ["confectionery", "bakery"]:
            categories.append("food")
        
        if tags.get("tourism") in ["gallery", "attraction"]:
            categories.append("culture")
        
        if tags.get("amenity") in ["arts_centre", "theatre", "place_of_worship"]:
            categories.append("culture")
        
        if tags.get("leisure") in ["park", "garden"]:
            categories.append("nature")
        
        if tags.get("natural") == "beach":
            categories.append("nature")
        
        return categories or ["mixed"]
    
    def _parse_overpass_response(self, data: Dict[str, Any]) -> List[Place]:
        """Parse Overpass API response into Place objects."""
        places = []
        seen_names: Set[str] = set()  # For deduplication
        
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name")
            
            if not name:
                continue
            
            # Skip duplicates (same name)
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())
            
            # Get coordinates
            if element["type"] == "node":
                lat, lng = element["lat"], element["lon"]
            elif element["type"] == "way" and "center" in element:
                lat, lng = element["center"]["lat"], element["center"]["lon"]
            elif element["type"] == "relation" and "center" in element:
                lat, lng = element["center"]["lat"], element["center"]["lon"]
            else:
                continue
            
            # Generate ID from coordinates
            place_id = f"osm_{abs(hash(f'{lat}_{lng}_{name}'))}_{len(places)}"
            
            # Parse opening status
            opening_hours = tags.get("opening_hours", "")
            opening_status = self._parse_opening_hours(opening_hours)
            
            # Skip places that are currently closed
            if opening_status == "closed":
                continue
            
            place = Place(
                id=place_id,
                name=name,
                lat=lat,
                lng=lng,
                categories=self._categorize_place(tags),
                tags=tags,
                opening_status=opening_status,
                facts=self._extract_facts(tags)
            )
            
            places.append(place)
            
            if len(places) >= config.MAX_PLACES:
                break
        
        return places
    
    async def fetch_places(
        self, 
        lat: float, 
        lng: float, 
        usable_minutes: int, 
        mode: str, 
        style: str
    ) -> List[Place]:
        """
        Fetch places from OpenStreetMap Overpass API.
        Returns empty list if API fails.
        """
        cache_key = f"places:{lat}:{lng}:{usable_minutes}:{mode}:{style}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        radius_km = self._calculate_radius(usable_minutes, mode)
        query = self._build_query(lat, lng, radius_km, style)
        
        for attempt in range(2):  # One retry
            try:
                async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
                    response = await client.post(
                        self.base_url,
                        data=query,
                        headers={"Content-Type": "text/plain"}
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    places = self._parse_overpass_response(data)
                    
                    cache.set(cache_key, places, config.CACHE_TTL)
                    return places
                    
            except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError) as e:
                if attempt == 0:
                    await asyncio.sleep(1)
                    continue
                # Return empty list on failure
                cache.set(cache_key, [], 300)  # Cache negative result briefly
                return []
        
        return []
    
    async def health_check(self) -> bool:
        """Check if Overpass API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Simple query to check if API responds
                query = "[out:json][timeout:5]; node(0); out;"
                response = await client.post(
                    self.base_url,
                    data=query,
                    headers={"Content-Type": "text/plain"}
                )
                return response.status_code == 200
        except:
            return False


places_service = PlacesService()