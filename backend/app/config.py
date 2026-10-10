"""Configuration management for LAYOVER backend."""

import os
from typing import Optional, List


class Config:
    """Application configuration from environment variables."""
    
    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    
    # Optional services
    OSRM_URL: Optional[str] = os.getenv("OSRM_URL")
    
    # CORS configuration
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    
    # Server configuration
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Feature flags
    EXPOSE_ANSWERS: bool = os.getenv("EXPOSE_ANSWERS", "true").lower() == "true"
    
    # API configuration
    REQUEST_TIMEOUT: int = 15  # Increased for comprehensive queries
    CACHE_TTL: int = 3600  # 1 hour
    MAX_PLACES: int = 50   # Increased for comprehensive scraping
    MAX_MISSIONS: int = 8
    
    # Travel speeds (km/h)
    WALK_SPEED: float = 4.5
    TRANSIT_SPEED: float = 15.0
    COMBINED_SPEED: float = 8.0
    DETOUR_FACTOR: float = 1.3
    
    @property
    def llm_configured(self) -> bool:
        """Check if LLM is properly configured."""
        if self.LLM_PROVIDER == "openai":
            return bool(self.OPENAI_API_KEY)
        elif self.LLM_PROVIDER == "anthropic":
            return bool(self.ANTHROPIC_API_KEY)
        elif self.LLM_PROVIDER == "google-genai":
            return bool(self.GOOGLE_API_KEY)
        return False


config = Config()