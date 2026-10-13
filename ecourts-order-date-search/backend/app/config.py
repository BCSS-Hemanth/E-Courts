"""
Application configuration for eCourts Order Date Search service.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")


class Settings:
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
    # (especially useful when external portal is geo-blocked, offline, or for automated tests)
    ECOURTS_MOCK_MODE: bool = os.getenv("ECOURTS_MOCK_MODE", "false").lower() in ("true", "1", "yes")

    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Maximum concurrent searches to protect memory
    MAX_CONCURRENT_SESSIONS: int = int(os.getenv("MAX_CONCURRENT_SESSIONS", "10"))


settings = Settings()
