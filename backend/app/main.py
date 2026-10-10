"""Main FastAPI application for LAYOVER backend."""

import uuid
import logging
import time
import re
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import config
from .schemas import (
    AdventureRequest, AdventureResponse, ReplanRequest,
    AnswerRequest, AnswerResponse, HintRequest, HintResponse,
    HealthResponse, GeocodeResponse, Location, Mission
)
from .services.geocode import geocoding_service
from .services.places import places_service
from .services.cache import cache
from .graph.build import adventure_graph
from .graph.state import AdventureState

# Configure logging
logging.basicConfig(
    level=logging.INFO if config.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="LAYOVER API",
    description="Time-aware mystery-adventure backend for travellers",
    version="1.0.0",
    docs_url="/docs" if config.DEBUG else None,
    redoc_url="/redoc" if config.DEBUG else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Basic rate limiting per IP (simplified)
from collections import defaultdict
request_counts = defaultdict(list)

# In-memory adventure store (would be replaced with a database)
adventure_store: Dict[str, Dict[str, Any]] = {}

def normalize_answer(answer: str) -> str:
    """Normalize an answer for comparison (matches frontend logic)."""
    # Replace non-alphanumeric with space, collapse whitespace
    normalized = re.sub(r'[^a-z0-9\s]', ' ', answer.lower())
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()


async def generate_adventure_internal(request: AdventureRequest) -> AdventureResponse:
    """Internal function to generate an adventure using the LangGraph pipeline."""
    
    # Initialize state
    initial_state: AdventureState = {
        "request": request,
        "start_location": None,
        "places": [],
        "places_source": "api", 
        "usable_minutes": 0,
        "shortlist": [],
        "travel_times": {},
        "visit_times": {},
        "costs": {},
        "return_times": {},
        "selected_ids": [],
        "llm_missions": {},
        "final_missions": [],
        "warnings": [],
        "source": "fallback",
        "error_count": 0,
        "last_error": None
    }
    
    # Run the pipeline
    try:
        result = await adventure_graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"Adventure generation pipeline failed: {e}")
        raise HTTPException(status_code=500, detail="Adventure generation failed")
    
    # Generate adventure ID and build response
    adventure_id = str(uuid.uuid4())[:8]
    title = f"LAYOVER Adventure in {result['start_location'].name}"
    
    # Remove answers and hints from missions if configured
    missions = result["final_missions"]
    if not config.EXPOSE_ANSWERS:
        for mission in missions:
            mission.answers = []
            mission.hints = []
    
    response = AdventureResponse(
        id=adventure_id,
        title=title,
        source=result["source"],
        usable_minutes=result["usable_minutes"],
        estimates_note="Travel and visit times are estimates",
        warnings=result["warnings"],
        start=result["start_location"],
        missions=missions
    )
    
    # Store adventure for later retrieval
    adventure_store[adventure_id] = {
        "response": response.model_dump(),
        "full_missions": result["final_missions"],  # Keep full data for answers/hints
        "created_at": time.time()
    }
    
    logger.info(f"Generated adventure {adventure_id} with {len(missions)} missions")
    return response


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    places_reachable = await places_service.health_check()
    
    return HealthResponse(
        status="ok",
        llm_configured=config.llm_configured,
        places_source_reachable=places_reachable
    )


def check_rate_limit(request: Request):
    """Simple rate limiting check."""
    client_ip = request.client.host
    now = time.time()
    
    # Clean old requests (older than 1 minute)
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip]
        if now - req_time < 60
    ]
    
    # Check if limit exceeded
    if len(request_counts[client_ip]) >= 10:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Add current request
    request_counts[client_ip].append(now)


@app.post("/api/adventures", response_model=AdventureResponse)
async def create_adventure(request: Request, adventure_request: AdventureRequest):
    """Generate a new adventure."""
    check_rate_limit(request)
    
    try:
        return await generate_adventure_internal(adventure_request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Adventure creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create adventure")


@app.get("/api/adventures/{adventure_id}", response_model=AdventureResponse)
async def get_adventure(adventure_id: str):
    """Get an existing adventure."""
    if adventure_id not in adventure_store:
        raise HTTPException(status_code=404, detail="Adventure not found")
    
    stored = adventure_store[adventure_id]
    return AdventureResponse.model_validate(stored["response"])


@app.post("/api/adventures/{adventure_id}/replan", response_model=AdventureResponse)
async def replan_adventure(adventure_id: str, replan_request: ReplanRequest):
    """Replan remaining missions for an adventure."""
    if adventure_id not in adventure_store:
        raise HTTPException(status_code=404, detail="Adventure not found")
    
    stored = adventure_store[adventure_id]
    original_response = AdventureResponse.model_validate(stored["response"])
    
    # Create new request based on current position and remaining resources
    new_request = AdventureRequest(
        start="Current location",
        start_lat=replan_request.current_lat,
        start_lng=replan_request.current_lng,
        minutes=replan_request.remaining_minutes,
        budget=replan_request.remaining_budget,
        buffer=10,  # Minimal buffer for replanning
        mode="both",  # Use both for replanning
        style="mixed",  # Use mixed style for replanning
        difficulty="medium"
    )
    
    try:
        # Generate new adventure from current position
        new_adventure = await generate_adventure_internal(new_request)
        
        # Filter out completed missions
        remaining_missions = [
            mission for mission in new_adventure.missions
            if mission.id not in replan_request.completed_ids
        ]
        
        # Update the response
        replanned_response = AdventureResponse(
            id=adventure_id,  # Keep same ID
            title=f"Replanned: {original_response.title}",
            source=new_adventure.source,
            usable_minutes=replan_request.remaining_minutes,
            estimates_note=new_adventure.estimates_note,
            warnings=new_adventure.warnings + ["Replanned from current location"],
            start=Location(
                name="Current location",
                lat=replan_request.current_lat,
                lng=replan_request.current_lng
            ),
            missions=remaining_missions
        )
        
        # Update stored adventure
        adventure_store[adventure_id]["response"] = replanned_response.model_dump()
        
        return replanned_response
        
    except Exception as e:
        logger.error(f"Replan failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to replan adventure")


@app.post("/api/adventures/{adventure_id}/answer", response_model=AnswerResponse)
async def check_answer(adventure_id: str, answer_request: AnswerRequest):
    """Check if an answer is correct."""
    if adventure_id not in adventure_store:
        raise HTTPException(status_code=404, detail="Adventure not found")
    
    stored = adventure_store[adventure_id]
    full_missions = stored["full_missions"]
    
    # Find the mission
    mission = None
    for m in full_missions:
        if m.id == answer_request.mission_id:
            mission = m
            break
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    # Check answer
    normalized_input = normalize_answer(answer_request.answer)
    normalized_answers = [normalize_answer(ans) for ans in mission.answers]
    
    correct = normalized_input in normalized_answers
    
    return AnswerResponse(correct=correct)


@app.post("/api/adventures/{adventure_id}/hint", response_model=HintResponse)
async def get_hint(adventure_id: str, hint_request: HintRequest):
    """Get a hint for a mission."""
    if adventure_id not in adventure_store:
        raise HTTPException(status_code=404, detail="Adventure not found")
    
    stored = adventure_store[adventure_id]
    full_missions = stored["full_missions"]
    
    # Find the mission
    mission = None
    for m in full_missions:
        if m.id == hint_request.mission_id:
            mission = m
            break
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    # Get hint by level (0-indexed)
    if hint_request.level < 0 or hint_request.level >= len(mission.hints):
        raise HTTPException(status_code=400, detail="Invalid hint level")
    
    hint = mission.hints[hint_request.level]
    
    return HintResponse(hint=hint)


@app.get("/api/geocode", response_model=GeocodeResponse) 
async def geocode_location(q: str):
    """Geocode a location query."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    result = await geocoding_service.geocode(q.strip())
    if not result:
        raise HTTPException(status_code=404, detail="Location not found")
    
    name, lat, lng = result
    return GeocodeResponse(name=name, lat=lat, lng=lng)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = time.time()
    
    # Don't log health checks in production
    if not config.DEBUG and request.url.path == "/api/health":
        response = await call_next(request)
        return response
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
    )
    
    return response


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Cleanup task for expired adventures (run periodically)
@app.on_event("startup")
async def startup_tasks():
    """Run startup tasks."""
    logger.info("LAYOVER backend starting up...")
    
    # Start cache cleanup task
    import asyncio
    async def cleanup_task():
        while True:
            await asyncio.sleep(3600)  # Run every hour
            cache.cleanup_expired()
            
            # Cleanup old adventures (older than 24 hours)
            cutoff = time.time() - 86400
            expired_ids = [
                aid for aid, data in adventure_store.items()
                if data["created_at"] < cutoff
            ]
            for aid in expired_ids:
                del adventure_store[aid]
            
            if expired_ids:
                logger.info(f"Cleaned up {len(expired_ids)} expired adventures")
    
    asyncio.create_task(cleanup_task())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.PORT,
        reload=config.DEBUG
    )