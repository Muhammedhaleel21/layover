"""State definitions for the LangGraph pipeline."""

from typing import List, Dict, Optional, Literal, TypedDict
from ..schemas import Place, AdventureRequest, Location, Mission


class AdventureState(TypedDict):
    """State for the adventure generation pipeline."""
    
    # Input configuration
    request: AdventureRequest
    start_location: Optional[Location]
    
    # Node outputs
    places: List[Place]
    places_source: Literal["api", "fallback"]
    
    usable_minutes: int
    shortlist: List[Place] 
    travel_times: Dict[str, int]
    visit_times: Dict[str, int]
    costs: Dict[str, int] 
    return_times: Dict[str, int]
    
    selected_ids: List[str]
    llm_missions: Dict[str, Dict[str, str]]  # place_id -> mission_data
    
    # Final outputs
    final_missions: List[Mission]
    warnings: List[str]
    source: Literal["ai", "fallback"]
    
    # Error handling
    error_count: int
    last_error: Optional[str]