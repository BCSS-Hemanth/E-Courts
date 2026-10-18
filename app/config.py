"""
Application configuration for eCourts Order Date Search service.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

# Load environment files
load_dotenv(BASE_DIR / ".env")


class Settings:
    # Directories
    BASE_DIR: Path = BASE_DIR
    APP_DIR: Path = APP_DIR
    PUBLIC_DIR: Path = APP_DIR / "public"
    LOCATIONS_FILE: Path = (
        APP_DIR / "data" / "court_locations.json"
        if (APP_DIR / "data" / "court_locations.json").exists()
        else APP_DIR / "court_locations.json"
    )

    # Official eCourts Court Orders URL
    ECOURTS_BASE_URL: str = os.getenv(
        "ECOURTS_BASE_URL",
        "https://services.ecourts.gov.in/ecourtindia_v6/?p=courtorder%2Findex",
    )

    # In-memory session lifetime before cleanup (seconds)
    SESSION_TIMEOUT_SECONDS: int = int(os.getenv("SESSION_TIMEOUT_SECONDS", "300"))

    # Playwright browser settings
    PLAYWRIGHT_HEADLESS: bool = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() in ("true", "1", "yes")
    PLAYWRIGHT_TIMEOUT_MS: int = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "30000"))

    # Mock mode flag: when set to true, simulates live behavior safely
    ECOURTS_MOCK_MODE: bool = os.getenv("ECOURTS_MOCK_MODE", "false").lower() in ("true", "1", "yes")

    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Maximum concurrent searches to protect memory
    MAX_CONCURRENT_SESSIONS: int = int(os.getenv("MAX_CONCURRENT_SESSIONS", "10"))


settings = Settings()
