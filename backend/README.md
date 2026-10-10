# LAYOVER Backend

Time-aware mystery-adventure backend for travellers using FastAPI and LangGraph.

## Features

- **Multi-agent pipeline** using LangGraph for adventure generation
- **Real data sources**: OpenStreetMap Overpass API, Nominatim geocoding
- **LLM integration**: Support for OpenAI, Anthropic, and Google Gemini models
- **Time-aware planning**: Protects return buffer time, handles delays
- **Fallback system**: Always returns playable content even when APIs fail
- **RESTful API**: Compatible with existing Next.js frontend

## Quick Start

### One-command development:
```bash
python dev.py
```

This script will:
1. Create a virtual environment
2. Install all dependencies  
3. Copy .env.example to .env
4. Start the development server

### Manual setup:

1. **Create virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Run development server:**
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration

### Required Environment Variables

For LLM functionality, set one of:

**OpenAI:**
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_key_here
```

**Anthropic:**
```bash
LLM_PROVIDER=anthropic  
LLM_MODEL=claude-3-haiku-20240307
ANTHROPIC_API_KEY=your_key_here
```

**Google Gemini:**
```bash
LLM_PROVIDER=google-genai
LLM_MODEL=gemini-1.5-flash
GOOGLE_API_KEY=your_key_here
```

### Optional Variables

```bash
# Optional OSRM routing service
OSRM_URL=http://router.project-osrm.org

# CORS origins (comma separated)
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Feature flags
EXPOSE_ANSWERS=false  # Hide answers/hints in mission response
```

## API Endpoints

### Core Endpoints

- `GET /api/health` - Health check with LLM and places source status
- `POST /api/adventures` - Generate new adventure 
- `GET /api/adventures/{id}` - Retrieve adventure by ID
- `POST /api/adventures/{id}/replan` - Replan remaining missions
- `GET /api/geocode?q=location` - Geocode a location string

### Game Endpoints

- `POST /api/adventures/{id}/answer` - Check mission answer
- `POST /api/adventures/{id}/hint` - Get mission hint

## Architecture

### LangGraph Pipeline

The backend uses a 4-node LangGraph pipeline:

1. **fetch_places**: Geocodes start location, queries Overpass API for places, falls back to curated data
2. **analyze_constraints**: Deterministic time/budget analysis, builds feasible greedy order  
3. **llm_curate**: LLM picks places and creates missions with riddles (skipped if no LLM configured)
4. **validate_and_assemble**: Validates LLM output, ensures constraints, assembles final missions

### Data Flow

```
Request → [Geocoding] → [Places API] → [Constraint Analysis] → [LLM Curation] → [Validation] → Response
                                                ↓
                                        [Fallback Data] (if APIs fail)
```

### Services

- `places.py`: OpenStreetMap Overpass API integration
- `geocode.py`: Nominatim geocoding service  
- `routing.py`: Travel time calculation (haversine + optional OSRM)
- `timecalc.py`: Time constraint utilities
- `fallback.py`: Curated Kozhikode data for offline mode
- `cache.py`: In-memory TTL cache for API responses

## Testing

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app tests/

# Run specific test file
python -m pytest tests/test_main.py -v
```

## Data Sources

### OpenStreetMap Overpass API

- **Free, no API key required**
- Searches within calculated radius based on time/mode
- Maps adventure styles to OSM tags:
  - `history`: historic=*, tourism=museum|monument
  - `food`: amenity=cafe|restaurant|marketplace, shop=confectionery|bakery  
  - `culture`: tourism=gallery|attraction, amenity=arts_centre|theatre|place_of_worship
  - `nature`: leisure=park|garden, natural=beach
  - `mixed`: All of the above

### Nominatim Geocoding

- **Free, no API key required** 
- Used only when request lacks coordinates
- Proper User-Agent header sent
- Respects usage policy with caching

### OSRM Routing (Optional)

- Enhanced travel time estimates if configured
- Falls back to haversine distance calculation
- Set `OSRM_URL` environment variable to enable

## Production Deployment

1. Set `DEBUG=false` in environment
2. Use production WSGI server (gunicorn recommended)
3. Configure proper CORS origins
4. Set up external database for adventure storage
5. Add proper logging and monitoring
6. Consider rate limiting at reverse proxy level

### Example Production Command

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Frontend Integration

The backend is designed to work with the existing Next.js frontend in `../frontend`. Key integration points:

- **Mission format**: Matches existing `Dest` type with camelCase field aliases
- **Answer normalization**: Uses same logic as frontend for consistency
- **Error handling**: Graceful fallbacks ensure frontend always gets playable content
- **CORS**: Configured for localhost:3000 by default

## Troubleshooting

### Common Issues

**"No LLM configured" in health check:**
- Set LLM_PROVIDER and corresponding API key in .env file

**"Places source unreachable":**  
- Check internet connection to overpass-api.de
- Verify no firewall blocking outbound HTTPS

**Empty mission lists:**
- Check if time/budget constraints are too restrictive  
- Review warnings in API response for specific issues
- Fallback data should still provide missions for Kozhikode

**Import errors:**
- Ensure PYTHONPATH includes backend directory
- Check virtual environment is activated
- Verify all requirements.txt dependencies installed

### Logs

The application logs requests and errors. In development mode (`DEBUG=true`), detailed logs are shown. Check logs for:

- API failures (Overpass, Nominatim)
- LLM errors and retry attempts  
- Constraint analysis results
- Cache hit/miss information