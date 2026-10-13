"""
Main FastAPI Application for eCourts Order Date Search.
Serves both backend REST API and the frontend static assets.
"""

import sys
import asyncio

# Ensure Windows ProactorEventLoop is used for Playwright subprocesses
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging

from app.config import settings
from app.routers.search import router as search_router
from app.services.session_manager import session_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ecourts_search")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting eCourts Order Date Search service...")
    yield
    logger.info("Shutting down eCourts Order Date Search service. Cleaning up active sessions...")
    await session_manager.cleanup_expired_sessions()


app = FastAPI(
    title="eCourts Order Date Search API",
    description="Standalone interface for Indian eCourts Order Date Search with Playwright scraping.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(search_router)

# Mount Frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Frontend index.html not found"}
else:
    logger.warning(f"Frontend directory not found at {FRONTEND_DIR}")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
