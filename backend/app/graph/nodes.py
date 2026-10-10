"""Node implementations for the LangGraph pipeline."""

import logging
from typing import List, Dict
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.chat_models import init_chat_model

from ..config import config
from ..schemas import Place, Mission, Location
from ..services.places import places_service
from ..services.geocode import geocoding_service
from ..services.routing import routing_service
from ..services.timecalc import calculate_usable_minutes, time_fits_with_buffer
from ..services.fallback import get_fallback_places, get_fallback_mission_data
from .state import AdventureState

logger = logging.getLogger(__name__)


class LLMCurationOutput(BaseModel):
    """Structured output from the LLM curation step."""
    selected_place_ids: List[str] = Field(
        description="List of 3-5 place IDs chosen from the shortlist, in order of visitation"
    )
    missions: List[Dict[str, str]] = Field(
        description="Mission data for each selected place"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "selected_place_ids": ["place1", "place2", "place3"],
                "missions": [
                    {
                        "place_id": "place1",
                        "title": "The Hidden Garden",
                        "intro": "Your first clue awaits in nature's embrace.",
                        "riddle": "Where ancient trees whisper secrets to those who listen?",
                        "hint1": "Look for the oldest tree in the area.",
                        "hint2": "The plaque tells the year it was planted.",
                        "answer1": "botanical garden",
                        "answer2": "botanic garden",
                        "story": "This garden was established in 1872 and houses rare species.",
                        "activity": "Find the heritage tree and read its plaque."
                    }
                ]
            }
        }


async def fetch_places_node(state: AdventureState) -> AdventureState:
    """
    Node 1: Fetch places from APIs or fallback data.
    
    - Geocodes start location if needed
    - Queries Overpass API for places
    - Falls back to curated data if API fails or returns < 3 places
    """
    request = state["request"]
    
    # Geocode start location if coordinates not provided
    if request.start_lat is None or request.start_lng is None:
        geocoded = await geocoding_service.geocode(request.start)
        if geocoded:
            name, lat, lng = geocoded
            start_location = Location(name=name, lat=lat, lng=lng)
        else:
            # Use default Kozhikode coordinates if geocoding fails
            start_location = Location(
                name=request.start,
                lat=11.2476,  # Kozhikode Railway Station
                lng=75.7836
            )
    else:
        start_location = Location(
            name=request.start,
            lat=request.start_lat,
            lng=request.start_lng
        )
    
    # Calculate usable minutes
    usable_minutes = calculate_usable_minutes(
        request.minutes,
        request.delay_minutes,
        request.scheduled_departure
    )
    
    # Fetch places from Overpass API
    places = await places_service.fetch_places(
        start_location.lat,
        start_location.lng,
        usable_minutes,
        request.mode,
        request.style
    )
    
    # Use fallback if API returned insufficient results
    if len(places) < 3:
        places = get_fallback_places()
        places_source = "fallback"
        logger.info(f"Using fallback places due to insufficient API results ({len(places)} places)")
    else:
        places_source = "api"
        logger.info(f"Fetched {len(places)} places from Overpass API")
    
    return {
        **state,
        "start_location": start_location,
        "usable_minutes": usable_minutes,
        "places": places,
        "places_source": places_source,
        "warnings": [],
        "error_count": 0
    }


async def analyze_constraints_node(state: AdventureState) -> AdventureState:
    """
    Node 2: Analyze time and budget constraints (deterministic).
    
    - Calculates travel/visit/return times and costs for each place
    - Filters out places that don't fit within constraints
    - Builds a feasible greedy order (nearest-neighbor)
    - Returns shortlist of up to 8 feasible places
    """
    places = state["places"]
    request = state["request"]
    start_location = state["start_location"]
    usable_minutes = state["usable_minutes"]
    
    # Calculate times and costs for all places
    travel_times = {}
    visit_times = {}
    costs = {}
    return_times = {}
    
    for place in places:
        # Travel time from start to place
        travel_min = await routing_service.calculate_travel_time(
            start_location.lat, start_location.lng,
            place.lat, place.lng,
            request.mode
        )
        travel_times[place.id] = travel_min
        
        # Visit time based on categories
        visit_min = routing_service.estimate_visit_time(place.categories)
        visit_times[place.id] = visit_min
        
        # Cost estimate based on categories  
        cost = routing_service.estimate_cost(place.categories)
        costs[place.id] = cost
        
        # Return time from place to start
        return_min = await routing_service.calculate_travel_time(
            place.lat, place.lng,
            start_location.lat, start_location.lng,
            request.mode
        )
        return_times[place.id] = return_min
    
    # Filter places that fit within individual constraints
    feasible_places = []
    for place in places:
        total_time_needed = (
            travel_times[place.id] +
            visit_times[place.id] +
            return_times[place.id] +
            request.buffer
        )
        
        if (total_time_needed <= usable_minutes and 
            costs[place.id] <= request.budget):
            feasible_places.append(place)
    
    # Build greedy order using nearest-neighbor from start
    ordered_places = []
    remaining_places = feasible_places.copy()
    current_lat, current_lng = start_location.lat, start_location.lng
    current_time = 0
    current_cost = 0
    
    while remaining_places and len(ordered_places) < config.MAX_MISSIONS:
        # Find nearest place that still fits
        best_place = None
        best_distance = float('inf')
        
        for place in remaining_places:
            # Calculate distance from current position
            travel_min = await routing_service.calculate_travel_time(
                current_lat, current_lng,
                place.lat, place.lng,
                request.mode
            )
            
            # Check if adding this place would fit
            total_new_time = (
                current_time +
                travel_min +
                visit_times[place.id] +
                return_times[place.id] +
                request.buffer
            )
            total_new_cost = current_cost + costs[place.id]
            
            if (total_new_time <= usable_minutes and 
                total_new_cost <= request.budget and
                travel_min < best_distance):
                best_place = place
                best_distance = travel_min
        
        if best_place is None:
            break  # No more places fit
        
        # Add the best place to our order
        ordered_places.append(best_place)
        remaining_places.remove(best_place)
        
        # Update current position and cumulative values
        current_lat, current_lng = best_place.lat, best_place.lng
        current_time += travel_times[best_place.id] + visit_times[best_place.id]
        current_cost += costs[best_place.id]
    
    # Take up to MAX_MISSIONS places for the shortlist
    shortlist = ordered_places[:config.MAX_MISSIONS]
    
    logger.info(f"Constraint analysis: {len(shortlist)} places fit within {usable_minutes}min and ₹{request.budget}")
    
    return {
        **state,
        "shortlist": shortlist,
        "travel_times": travel_times,
        "visit_times": visit_times,
        "costs": costs,
        "return_times": return_times
    }


async def llm_curate_node(state: AdventureState) -> AdventureState:
    """
    Node 3: LLM curates missions from shortlist.
    
    - Sends shortlist to LLM with style/difficulty parameters
    - LLM picks 3-5 places and creates missions with titles, riddles, etc.
    - Uses structured output to ensure valid JSON response
    """
    shortlist = state["shortlist"]
    request = state["request"]
    
    if not config.llm_configured:
        logger.info("No LLM configured, skipping curation")
        return {
            **state,
            "selected_ids": [],
            "llm_missions": {},
            "source": "fallback"
        }
    
    if not shortlist:
        logger.warning("No places in shortlist for LLM curation")
        return {
            **state,
            "selected_ids": [],
            "llm_missions": {},
            "source": "fallback"
        }
    
    try:
        # Initialize the chat model
        chat_model = init_chat_model(
            config.LLM_PROVIDER,
            model=config.LLM_MODEL,
            temperature=0.7
        )
        
        # Use structured output
        structured_model = chat_model.with_structured_output(LLMCurationOutput)
        
        # Build the prompt
        places_json = []
        for place in shortlist:
            places_json.append({
                "id": place.id,
                "name": place.name,
                "lat": place.lat,
                "lng": place.lng,
                "categories": place.categories,
                "facts": place.facts,
                "travel_min": state["travel_times"][place.id],
                "visit_min": state["visit_times"][place.id],
                "cost": state["costs"][place.id]
            })
        
        system_prompt = f"""You are creating mystery adventure missions for travelers in Kozhikode, India.

CRITICAL RULES:
1. NEVER invent places, coordinates, opening hours, prices, schedules, or historical facts
2. Use ONLY the facts provided in the place data
3. Riddles must NOT contain the place name directly
4. Each mission needs: title, intro, riddle, 2 hints, accepted answers (including real name + variants), story, activity
5. Difficulty '{request.difficulty}' controls riddle obscurity (easy=obvious clues, challenging=subtle)
6. Style '{request.style}' should influence your selection priority
7. Choose 3-5 places from the shortlist in a logical visiting order
8. All suggestions must be safe and appropriate for daytime visitors
9. Accepted answers must include the real place name and reasonable variants

Available places (choose 3-5): {places_json}

Time available: {state['usable_minutes']} minutes
Budget: ₹{request.budget}"""

        user_prompt = f"""Create mystery missions for a {request.style} adventure at {request.difficulty} difficulty level. Select 3-5 places from the provided shortlist and create engaging riddles that don't directly name the places. Use only the provided facts - never invent information."""

        # Get LLM response
        response = await structured_model.ainvoke([
            ("system", system_prompt),
            ("human", user_prompt)
        ])
        
        # Validate the response
        selected_ids = response.selected_place_ids
        missions_data = {}
        
        # Convert missions list to dict keyed by place_id
        for mission in response.missions:
            place_id = mission.get("place_id")
            if place_id in selected_ids:
                missions_data[place_id] = mission
        
        logger.info(f"LLM curated {len(selected_ids)} missions")
        
        return {
            **state,
            "selected_ids": selected_ids,
            "llm_missions": missions_data,
            "source": "ai"
        }
        
    except Exception as e:
        logger.error(f"LLM curation failed: {e}")
        error_count = state.get("error_count", 0) + 1
        return {
            **state,
            "selected_ids": [],
            "llm_missions": {},
            "source": "fallback",
            "error_count": error_count,
            "last_error": str(e)
        }


async def validate_and_assemble_node(state: AdventureState) -> AdventureState:
    """
    Node 4: Validate LLM output and assemble final missions.
    
    - Validates LLM selections are from shortlist
    - Checks riddles don't contain place names
    - Re-runs time/budget constraints on LLM order
    - Falls back to templates on validation failure
    - Always returns something playable
    """
    shortlist = state["shortlist"]
    selected_ids = state["selected_ids"]
    llm_missions = state["llm_missions"]
    request = state["request"]
    start_location = state["start_location"]
    
    final_missions = []
    warnings = state.get("warnings", [])
    source = state.get("source", "fallback")
    
    # Create lookup for shortlisted places
    shortlist_by_id = {place.id: place for place in shortlist}
    
    if not selected_ids or not shortlist:
        # No LLM curation or empty shortlist - use fallback
        logger.info("Using fallback missions due to empty selection")
        selected_ids = [place.id for place in shortlist[:3]]
        source = "fallback"
    
    # Validate and filter selected IDs
    valid_ids = []
    for place_id in selected_ids:
        if place_id not in shortlist_by_id:
            warnings.append(f"LLM selected unknown place ID: {place_id}")
            continue
        valid_ids.append(place_id)
    
    # Re-run time and budget check on the LLM order
    cumulative_time = 0
    cumulative_cost = 0
    final_valid_ids = []
    
    current_lat, current_lng = start_location.lat, start_location.lng
    
    for place_id in valid_ids:
        place = shortlist_by_id[place_id]
        
        # Calculate travel time from current position to this place
        travel_min = await routing_service.calculate_travel_time(
            current_lat, current_lng,
            place.lat, place.lng,
            request.mode
        )
        
        visit_min = state["visit_times"][place_id]
        return_min = state["return_times"][place_id] 
        cost = state["costs"][place_id]
        
        # Check if adding this mission would exceed constraints
        new_total_time = cumulative_time + travel_min + visit_min + return_min + request.buffer
        new_total_cost = cumulative_cost + cost
        
        if new_total_time <= state["usable_minutes"] and new_total_cost <= request.budget:
            final_valid_ids.append(place_id)
            cumulative_time += travel_min + visit_min
            cumulative_cost += cost
            current_lat, current_lng = place.lat, place.lng
        else:
            warnings.append(f"Trimmed mission {place.name} - would exceed time/budget limits")
            break
    
    # Build final missions
    for i, place_id in enumerate(final_valid_ids):
        place = shortlist_by_id[place_id]
        
        # Get mission data from LLM or fallback
        if source == "ai" and place_id in llm_missions:
            mission_data = llm_missions[place_id]
            
            # Validate riddle doesn't contain place name
            riddle = mission_data.get("riddle", "")
            if place.name.lower() in riddle.lower():
                warnings.append(f"Riddle for {place.name} contains the place name, using fallback")
                mission_data = get_fallback_mission_data(place_id)
                source = "fallback"
        else:
            mission_data = get_fallback_mission_data(place_id)
        
        # Calculate final travel time (from previous location or start)
        if i == 0:
            travel_min = state["travel_times"][place_id]
        else:
            prev_place = shortlist_by_id[final_valid_ids[i-1]]
            travel_min = await routing_service.calculate_travel_time(
                prev_place.lat, prev_place.lng,
                place.lat, place.lng,
                request.mode
            )
        
        # Build mission object
        mission = Mission(
            id=place.id,
            name=place.name,
            lat=place.lat,
            lng=place.lng,
            travel_min=travel_min,
            visit_min=state["visit_times"][place_id],
            return_min=state["return_times"][place_id],
            cost=state["costs"][place_id],
            title=mission_data.get("title", f"Mission at {place.name}"),
            intro=mission_data.get("intro", "Explore this interesting location."),
            riddle=mission_data.get("riddle", "What makes this place special?"),
            hints=mission_data.get("hints", ["Look around for clues.", "Ask locals if needed."]),
            answers=mission_data.get("answers", [place.name.lower()]),
            story=mission_data.get("story", "This place has its own unique character."),
            activity=mission_data.get("activity", "Take time to observe your surroundings.")
        )
        
        final_missions.append(mission)
    
    if not final_missions:
        warnings.append("No missions fit within your time and budget constraints")
    
    logger.info(f"Assembled {len(final_missions)} final missions with source: {source}")
    
    return {
        **state,
        "final_missions": final_missions,
        "warnings": warnings,
        "source": source
    }