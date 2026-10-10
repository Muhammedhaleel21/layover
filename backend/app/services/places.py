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
        """Get comprehensive Overpass query filters for scraping nearby places."""
        filters = {
            "history": '''
                (
                  nwr["historic"~"^(monument|memorial|castle|fort|ruins|archaeological_site|battlefield|building|church|mosque|temple|synagogue|palace|manor|city_gate|tower|statue|tomb|wayside_cross|boundary_stone)$"]["name"];
                  nwr["tourism"~"^(museum|heritage|attraction)$"]["name"];
                  nwr["amenity"~"^(place_of_worship|library|archive)$"]["name"]["historic"];
                  nwr["building"~"^(historic|heritage|temple|church|cathedral|mosque|synagogue)$"]["name"];
                  nwr["man_made"~"^(tower|lighthouse|windmill)$"]["name"]["historic"];
                )
            ''',
            "food": '''
                (
                  nwr["amenity"~"^(restaurant|cafe|fast_food|food_court|pub|bar|biergarten|ice_cream|marketplace|street_vendor)$"]["name"];
                  nwr["shop"~"^(bakery|confectionery|chocolate|tea|coffee|spices|deli|supermarket|convenience|grocery|butcher|fishmonger|greengrocer|alcohol|wine|beverages|dairy|farm)$"]["name"];
                  nwr["cuisine"~"."]["name"];
                  nwr["tourism"="attraction"]["name"]["cuisine"];
                  nwr["landuse"="commercial"]["name"]["shop"];
                )
            ''',
            "culture": '''
                (
                  nwr["tourism"~"^(museum|gallery|attraction|artwork|viewpoint)$"]["name"];
                  nwr["amenity"~"^(theatre|cinema|arts_centre|community_centre|social_centre|music_venue|nightclub|studio|exhibition_hall|planetarium)$"]["name"];
                  nwr["leisure"~"^(sports_centre|stadium|swimming_pool|fitness_centre|dance|amusement_arcade)$"]["name"];
                  nwr["craft"~"^(pottery|sculptor|painter|jeweller|tailor|shoemaker|carpenter|blacksmith)$"]["name"];
                  nwr["shop"~"^(books|music|art|antiques|gift|jewelry|clothes|shoes|florist|toys|games|sports)$"]["name"];
                  nwr["building"~"^(civic|public|cultural)$"]["name"];
                )
            ''',
            "nature": '''
                (
                  nwr["leisure"~"^(park|garden|nature_reserve|playground|picnic_table|beach_resort|marina|fishing|bird_hide)$"]["name"];
                  nwr["natural"~"^(beach|lake|river|waterfall|spring|cave|peak|hill|forest|wood|grassland|wetland|coastline|bay)$"]["name"];
                  nwr["landuse"~"^(forest|recreation_ground|village_green|meadow|orchard|vineyard)$"]["name"];
                  nwr["tourism"~"^(zoo|aquarium|theme_park|picnic_site|camp_site)$"]["name"];
                  nwr["amenity"~"^(fountain|bench|shelter)$"]["name"]["natural"];
                  nwr["boundary"="national_park"]["name"];
                  nwr["protected_area"="yes"]["name"];
                )
            ''',
            "mixed": '''
                (
                  // Historical places
                  nwr["historic"~"^(monument|memorial|castle|fort|ruins|archaeological_site|battlefield|building|church|mosque|temple|synagogue|palace|manor|city_gate|tower|statue|tomb|wayside_cross|boundary_stone)$"]["name"];
                  nwr["tourism"~"^(museum|heritage|attraction)$"]["name"];
                  
                  // Food and shops
                  nwr["amenity"~"^(restaurant|cafe|fast_food|food_court|pub|bar|biergarten|ice_cream|marketplace|street_vendor)$"]["name"];
                  nwr["shop"~"^(bakery|confectionery|chocolate|tea|coffee|spices|deli|supermarket|convenience|grocery|butcher|fishmonger|greengrocer|alcohol|wine|beverages|dairy|farm|books|music|art|antiques|gift|jewelry|clothes|shoes|florist|toys|games|sports)$"]["name"];
                  
                  // Cultural venues
                  nwr["amenity"~"^(theatre|cinema|arts_centre|community_centre|social_centre|music_venue|nightclub|studio|exhibition_hall|planetarium|place_of_worship|library)$"]["name"];
                  nwr["leisure"~"^(sports_centre|stadium|swimming_pool|fitness_centre|dance|amusement_arcade)$"]["name"];
                  nwr["craft"~"^(pottery|sculptor|painter|jeweller|tailor|shoemaker|carpenter|blacksmith)$"]["name"];
                  
                  // Nature and recreation
                  nwr["leisure"~"^(park|garden|nature_reserve|playground|picnic_table|beach_resort|marina|fishing|bird_hide)$"]["name"];
                  nwr["natural"~"^(beach|lake|river|waterfall|spring|cave|peak|hill|forest|wood|grassland|wetland|coastline|bay)$"]["name"];
                  nwr["landuse"~"^(forest|recreation_ground|village_green|meadow|orchard|vineyard)$"]["name"];
                  nwr["tourism"~"^(zoo|aquarium|theme_park|picnic_site|camp_site|viewpoint)$"]["name"];
                  
                  // Mixed attractions
                  nwr["tourism"="attraction"]["name"];
                  nwr["building"~"^(historic|heritage|civic|public|cultural|temple|church|cathedral|mosque|synagogue)$"]["name"];
                )
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
        
        # Always use minimum 5km radius for comprehensive scraping as requested
        # Cap maximum to 20km for performance
        return max(5.0, min(20.0, radius_km))
    
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
        """Extract comprehensive factual information from OSM tags."""
        facts = []
        
        # Basic information
        if "name" in tags:
            facts.append(f"Name: {tags['name']}")
        
        # Alternative names
        if "name:en" in tags and tags["name:en"] != tags.get("name", ""):
            facts.append(f"English name: {tags['name:en']}")
        
        if "alt_name" in tags:
            facts.append(f"Also known as: {tags['alt_name']}")
        
        # Historical information
        if "historic" in tags:
            if tags["historic"] != "yes":
                facts.append(f"Historic type: {tags['historic']}")
        
        if "heritage" in tags:
            facts.append(f"Heritage status: {tags['heritage']}")
        
        if "start_date" in tags:
            facts.append(f"Established: {tags['start_date']}")
        
        if "architect" in tags:
            facts.append(f"Architect: {tags['architect']}")
        
        # Tourism and attraction info
        if "tourism" in tags:
            facts.append(f"Tourism type: {tags['tourism']}")
        
        if "attraction" in tags:
            facts.append(f"Attraction type: {tags['attraction']}")
        
        # Food and dining
        if "cuisine" in tags:
            facts.append(f"Cuisine: {tags['cuisine']}")
        
        if "diet:vegetarian" in tags:
            facts.append(f"Vegetarian options: {tags['diet:vegetarian']}")
        
        if "diet:vegan" in tags:
            facts.append(f"Vegan options: {tags['diet:vegan']}")
        
        # Shopping
        if "shop" in tags:
            facts.append(f"Shop type: {tags['shop']}")
        
        if "brand" in tags:
            facts.append(f"Brand: {tags['brand']}")
        
        # Cultural venues
        if "amenity" in tags:
            facts.append(f"Facility type: {tags['amenity']}")
        
        if "craft" in tags:
            facts.append(f"Craft type: {tags['craft']}")
        
        # Natural features
        if "natural" in tags:
            facts.append(f"Natural feature: {tags['natural']}")
        
        if "leisure" in tags:
            facts.append(f"Leisure facility: {tags['leisure']}")
        
        # Detailed descriptions
        if "description" in tags:
            facts.append(f"Description: {tags['description']}")
        
        if "inscription" in tags:
            facts.append(f"Inscription: {tags['inscription']}")
        
        # External references
        if "wikipedia" in tags:
            facts.append(f"Wikipedia: {tags['wikipedia']}")
        
        if "wikidata" in tags:
            facts.append(f"Wikidata ID: {tags['wikidata']}")
        
        # Contact information
        if "website" in tags:
            facts.append(f"Website: {tags['website']}")
        
        if "phone" in tags:
            facts.append(f"Phone: {tags['phone']}")
        
        if "email" in tags:
            facts.append(f"Email: {tags['email']}")
        
        # Operating information
        if "opening_hours" in tags:
            facts.append(f"Opening hours: {tags['opening_hours']}")
        
        if "fee" in tags:
            facts.append(f"Entry fee: {tags['fee']}")
        
        # Address information
        address_parts = []
        for key in ["addr:housenumber", "addr:street", "addr:city", "addr:postcode"]:
            if key in tags:
                address_parts.append(tags[key])
        
        if address_parts:
            facts.append(f"Address: {', '.join(address_parts)}")
        
        # Accessibility
        if "wheelchair" in tags:
            facts.append(f"Wheelchair accessible: {tags['wheelchair']}")
        
        # Building information
        if "building" in tags and tags["building"] != "yes":
            facts.append(f"Building type: {tags['building']}")
        
        if "architectural_style" in tags:
            facts.append(f"Architectural style: {tags['architectural_style']}")
        
        # Significance and awards
        if "significance" in tags:
            facts.append(f"Significance: {tags['significance']}")
        
        if "designation" in tags:
            facts.append(f"Designation: {tags['designation']}")
        
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
        """Categorize a place based on its comprehensive OSM tags."""
        categories = []
        
        # Historical categories
        if any(key in tags for key in ["historic", "heritage", "archaeological_site"]):
            categories.append("history")
        
        if tags.get("tourism") in ["museum", "heritage", "monument"]:
            categories.append("history")
        
        if tags.get("building") in ["historic", "heritage", "temple", "church", "cathedral", "mosque", "synagogue", "palace", "castle", "manor"]:
            categories.append("history")
        
        # Food categories
        if tags.get("amenity") in ["restaurant", "cafe", "fast_food", "food_court", "pub", "bar", "biergarten", "ice_cream", "marketplace", "street_vendor"]:
            categories.append("food")
        
        if tags.get("shop") in ["bakery", "confectionery", "chocolate", "tea", "coffee", "spices", "deli", "supermarket", "convenience", "grocery", "butcher", "fishmonger", "greengrocer", "alcohol", "wine", "beverages", "dairy", "farm"]:
            categories.append("food")
        
        if "cuisine" in tags:
            categories.append("food")
        
        # Cultural categories
        if tags.get("tourism") in ["gallery", "attraction", "artwork", "viewpoint"]:
            categories.append("culture")
        
        if tags.get("amenity") in ["theatre", "cinema", "arts_centre", "community_centre", "social_centre", "music_venue", "nightclub", "studio", "exhibition_hall", "planetarium", "place_of_worship", "library"]:
            categories.append("culture")
        
        if tags.get("leisure") in ["sports_centre", "stadium", "swimming_pool", "fitness_centre", "dance", "amusement_arcade"]:
            categories.append("culture")
        
        if tags.get("craft") in ["pottery", "sculptor", "painter", "jeweller", "tailor", "shoemaker", "carpenter", "blacksmith"]:
            categories.append("culture")
        
        if tags.get("shop") in ["books", "music", "art", "antiques", "gift", "jewelry", "clothes", "shoes", "florist", "toys", "games", "sports"]:
            categories.append("culture")
        
        # Nature categories
        if tags.get("leisure") in ["park", "garden", "nature_reserve", "playground", "picnic_table", "beach_resort", "marina", "fishing", "bird_hide"]:
            categories.append("nature")
        
        if tags.get("natural") in ["beach", "lake", "river", "waterfall", "spring", "cave", "peak", "hill", "forest", "wood", "grassland", "wetland", "coastline", "bay"]:
            categories.append("nature")
        
        if tags.get("landuse") in ["forest", "recreation_ground", "village_green", "meadow", "orchard", "vineyard"]:
            categories.append("nature")
        
        if tags.get("tourism") in ["zoo", "aquarium", "theme_park", "picnic_site", "camp_site"]:
            categories.append("nature")
        
        if tags.get("boundary") == "national_park" or tags.get("protected_area") == "yes":
            categories.append("nature")
        
        # Default to mixed if no specific category or multiple categories
        if not categories:
            categories.append("mixed")
        
        return categories
    
    def _parse_overpass_response(self, data: Dict[str, Any]) -> List[Place]:
        """Parse comprehensive Overpass API response into Place objects."""
        places = []
        seen_names: Set[str] = set()  # For deduplication
        seen_coords: Set[str] = set()  # For coordinate-based deduplication
        
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name")
            
            if not name:
                continue
            
            # Skip duplicates (same name)
            name_key = name.lower().strip()
            if name_key in seen_names:
                continue
            
            # Get coordinates with multiple fallback methods
            lat, lng = None, None
            
            if element["type"] == "node":
                lat, lng = element["lat"], element["lon"]
            elif element["type"] == "way":
                # Try center first, then calculate from nodes
                if "center" in element:
                    lat, lng = element["center"]["lat"], element["center"]["lon"]
                elif "nodes" in element and len(element["nodes"]) > 0:
                    # Calculate centroid from node coordinates if available
                    node_coords = []
                    for node_data in element.get("geometry", []):
                        if "lat" in node_data and "lon" in node_data:
                            node_coords.append((node_data["lat"], node_data["lon"]))
                    
                    if node_coords:
                        lat = sum(coord[0] for coord in node_coords) / len(node_coords)
                        lng = sum(coord[1] for coord in node_coords) / len(node_coords)
            elif element["type"] == "relation":
                if "center" in element:
                    lat, lng = element["center"]["lat"], element["center"]["lon"]
            
            if lat is None or lng is None:
                continue
            
            # Coordinate-based deduplication (within 100m)
            coord_key = f"{lat:.3f},{lng:.3f}"
            if coord_key in seen_coords:
                continue
            
            # Generate more descriptive ID
            element_id = element.get("id", "unknown")
            place_id = f"osm_{element['type']}_{element_id}_{len(places)}"
            
            # Parse opening status
            opening_hours = tags.get("opening_hours", "")
            opening_status = self._parse_opening_hours(opening_hours)
            
            # Skip places that are currently closed (but keep unknown status)
            if opening_status == "closed":
                continue
            
            # Extract comprehensive facts
            facts = self._extract_facts(tags)
            
            # Categorize the place
            categories = self._categorize_place(tags)
            
            place = Place(
                id=place_id,
                name=name,
                lat=lat,
                lng=lng,
                categories=categories,
                tags=tags,
                opening_status=opening_status,
                facts=facts
            )
            
            places.append(place)
            seen_names.add(name_key)
            seen_coords.add(coord_key)
            
            # Increased cap for comprehensive scraping (from 25 to 50)
            if len(places) >= 50:
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