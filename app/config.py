"""
Configuration settings for FIFA 2026 CrowdFlow Assist.
Loads environment variables and sets defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

class Config:
    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Security
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "fifa_world_cup_2026_operations_secret_key")
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # LLM Settings
    USE_MOCK_LLM: bool = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Stadium parameters
    STADIUM_NAME: str = os.getenv("STADIUM_NAME", "MetLife Stadium")
    STADIUM_CAPACITY: int = int(os.getenv("STADIUM_CAPACITY", "82500"))

    # In-memory cache durations (in seconds)
    ROUTE_CACHE_TTL: int = 300       # 5 minutes
    TRANSLATION_CACHE_TTL: int = 3600 # 1 hour

# Global configuration instance
settings = Config()
