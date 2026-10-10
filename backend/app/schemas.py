"""Pydantic schemas for LAYOVER backend."""

from datetime import datetime
from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field


class AdventureRequest(BaseModel):
    """Request to generate an adventure."""
    start: str = Field(..., description="Starting location name")
    start_lat: Optional[float] = Field(None, description="Starting latitude")
    start_lng: Optional[float] = Field(None, description="Starting longitude")
    minutes: int = Field(..., ge=30, le=720, description="Available time in minutes")
    budget: int = Field(..., ge=0, le=20000, description="Budget in INR")
    buffer: int = Field(..., ge=10, le=180, description="Return buffer in minutes")
    mode: Literal["walk", "transit", "both"] = Field(..., description="Travel mode")
    style: Literal["history", "food", "culture", "nature", "mixed"] = Field(..., description="Adventure style")
    difficulty: Literal["easy", "medium", "challenging"] = Field(..., description="Riddle difficulty")
    delay_minutes: Optional[int] = Field(None, description="Delay minutes from train/bus")
    scheduled_departure: Optional[datetime] = Field(None, description="Original departure time")


class Location(BaseModel):
    """A geographic location."""
    name: str
    lat: float
    lng: float


class Mission(BaseModel):
    """A mission/destination with all required data for frontend."""
    id: str
    name: str
    lat: float
    lng: float
    travel_min: int = Field(..., alias="travelMin")
    visit_min: int = Field(..., alias="visitMin") 
    return_min: int = Field(..., alias="returnMin")
    cost: int
    title: str
    intro: str
    riddle: str
    hints: List[str]
    answers: List[str]
    story: str
    activity: str

    class Config:
        populate_by_name = True


class AdventureResponse(BaseModel):
    """Response containing generated adventure."""
    id: str
    title: str
    source: Literal["ai", "fallback"]
    usable_minutes: int
    estimates_note: str = "Travel and visit times are estimates"
    warnings: List[str] = []
    start: Location
    missions: List[Mission]


class ReplanRequest(BaseModel):
    """Request to replan remaining missions."""
    remaining_minutes: int
    remaining_budget: int
    current_lat: float
    current_lng: float
    completed_ids: List[str]


class AnswerRequest(BaseModel):
    """Request to check an answer."""
    mission_id: str
    answer: str


class AnswerResponse(BaseModel):
    """Response to answer check."""
    correct: bool


class HintRequest(BaseModel):
    """Request for a hint."""
    mission_id: str
    level: int


class HintResponse(BaseModel):
    """Response containing a hint."""
    hint: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    llm_configured: bool
    places_source_reachable: bool


class GeocodeResponse(BaseModel):
    """Geocoding response."""
    name: str
    lat: float
    lng: float


# Internal schemas for the pipeline

class Place(BaseModel):
    """A place found from OpenStreetMap."""
    id: str
    name: str
    lat: float
    lng: float
    categories: List[str]
    tags: Dict[str, str]
    opening_status: Literal["open", "closed", "unknown"]
    facts: List[str]


class ConstraintAnalysis(BaseModel):
    """Analysis of time and budget constraints."""
    usable_minutes: int
    shortlist: List[Place]
    travel_times: Dict[str, int]
    visit_times: Dict[str, int] 
    costs: Dict[str, int]
    return_times: Dict[str, int]


class LLMCuration(BaseModel):
    """LLM curated missions."""
    selected_ids: List[str]
    missions_data: Dict[str, Dict[str, str]]  # mission_id -> {title, intro, riddle, etc}