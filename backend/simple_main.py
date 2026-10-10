#!/usr/bin/env python3
"""Simplified FastAPI server for testing core endpoints without LangGraph."""

import uuid
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Simplified schemas for testing
class AdventureRequest(BaseModel):
    start: str
    start_lat: Optional[float] = None
    start_lng: Optional[float] = None
    minutes: int
    budget: int
    buffer: int
    mode: str
    style: str
    difficulty: str
    delay_minutes: Optional[int] = None

class Location(BaseModel):
    name: str
    lat: float
    lng: float

class Mission(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    travelMin: int
    visitMin: int
    returnMin: int
    cost: int
    title: str
    intro: str
    riddle: str
    hints: list[str]
    answers: list[str]
    story: str
    activity: str

class AdventureResponse(BaseModel):
    id: str
    title: str
    source: str
    usableMinutes: int
    estimatesNote: str
    warnings: list[str]
    start: Location
    missions: list[Mission]

class HealthResponse(BaseModel):
    status: str = "ok"
    llmConfigured: bool = False
    placesSourceReachable: bool = True

class GeocodeResponse(BaseModel):
    name: str
    lat: float
    lng: float

# Create app
app = FastAPI(title="LAYOVER API (Test Mode)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Fallback data
FALLBACK_MISSIONS = [
    Mission(
        id="mananchira",
        name="Mananchira Square",
        lat=11.2588,
        lng=75.7804,
        travelMin=20,
        visitMin=30,
        returnMin=20,
        cost=40,
        title="The Quiet Centre",
        intro="The case begins where the city goes still.",
        riddle="A park wraps around still water in the middle of a busy city. Locals gather on its lawns, and the square is named for the water itself, not for any person. Where do you stand?",
        hints=[
            "Think of a public square with a large tank (pond) at its heart.",
            "The name starts with 'Mana' and ends in 'chira'."
        ],
        answers=[
            "mananchira",
            "mananchira square",
            "mananchira maidan",
            "mananchira veedan maidan"
        ],
        story="Mananchira Square is a public park built around a large tank in the heart of Kozhikode. It is a favourite spot for walks and gatherings.",
        activity="Walk once around the tank and note what people are doing on the lawns."
    ),
    Mission(
        id="smstreet",
        name="SM Street (Mittai Theruvu)",
        lat=11.2575,
        lng=75.781,
        travelMin=10,
        visitMin=30,
        returnMin=15,
        cost=120,
        title="The Sweet Trail",
        intro="The next lead is something you can smell before you see it.",
        riddle="A crowded lane takes its popular name from sugar. Shops here are known for a sticky, ghee-rich sweet sold by weight. Name the street.",
        hints=[
            "Its nickname in Malayalam means 'sweet street'.",
            "SM stands for 'Sweetmeat'."
        ],
        answers=[
            "sm street",
            "s m street",
            "mittai theruvu",
            "mithai theruvu",
            "sweet meat street",
            "sweetmeat street",
            "mittayi theruvu"
        ],
        story="SM Street, officially Sweet Meat Street and widely called Mittai Theruvu, is a busy shopping lane in central Kozhikode known for its sweets, especially halwa.",
        activity="Buy a small portion of halwa to share. Prices vary by shop, so ask before buying."
    ),
    Mission(
        id="beach",
        name="Kozhikode Beach",
        lat=11.2623,
        lng=75.767,
        travelMin=20,
        visitMin=40,
        returnMin=30,
        cost=50,
        title="Where the City Meets the Sea",
        intro="Final chapter. Follow the sound of the waves.",
        riddle="The Arabian Sea ends this case. Old piers once reached out from this shore, and people come here as the sun drops. Where does the trail end?",
        hints=[
            "Look west. The city's main public shoreline.",
            "Remains of old piers stand in its waters."
        ],
        answers=[
            "kozhikode beach",
            "calicut beach",
            "beach",
            "kozhikode beach front",
            "calicut beach front"
        ],
        story="Kozhikode Beach is the city's main public shoreline on the Arabian Sea, popular in the evenings. Remains of old piers stand offshore.",
        activity="Watch the water from the shore. Stay on the open sand, away from the waterline when it is rough."
    )
]

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()

@app.post("/api/adventures", response_model=AdventureResponse)
async def create_adventure(request: AdventureRequest):
    adventure_id = str(uuid.uuid4())[:8]
    
    # Simple constraint filtering based on time and budget
    feasible_missions = []
    for mission in FALLBACK_MISSIONS:
        total_time = mission.travelMin + mission.visitMin + mission.returnMin + request.buffer
        if total_time <= request.minutes and mission.cost <= request.budget:
            feasible_missions.append(mission)
    
    return AdventureResponse(
        id=adventure_id,
        title=f"LAYOVER Adventure in {request.start}",
        source="fallback",
        usableMinutes=request.delay_minutes or request.minutes,
        estimatesNote="Travel and visit times are estimates",
        warnings=[] if feasible_missions else ["Limited missions available for your constraints"],
        start=Location(
            name=request.start,
            lat=request.start_lat or 11.2476,
            lng=request.start_lng or 75.7836
        ),
        missions=feasible_missions
    )

@app.get("/api/geocode", response_model=GeocodeResponse)
async def geocode(q: str):
    # Simple mock geocoding for Kozhikode
    return GeocodeResponse(
        name=f"{q}, Kozhikode, Kerala, India",
        lat=11.2476,
        lng=75.7836
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)