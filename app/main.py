"""
Main FastAPI Application for eCourts Order Date Search.
Serves both backend REST API and the frontend static assets.
"""

import sys
import asyncio

# ProactorEventLoop is default on Windows since Python 3.8; only set explicitly on legacy Python versions (<3.14)
if sys.platform == "win32" and sys.version_info < (3, 14):
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
from app.order_date_search import router as order_date_search_router
from app.cnr_search import router as cnr_search_router
from app.search_session_manager import session_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ecourts_search")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting eCourts Search service (Order Date & CNR)...")
    yield
    logger.info("Shutting down eCourts Search service. Cleaning up active sessions...")
    await session_manager.cleanup_expired_sessions()


app = FastAPI(
    title="eCourts Judicial Search API",
    description="Standalone interface for Indian eCourts Order Date Search and CNR Search with automated scraping.",
    version="1.1.0",
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

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Include API Routers
app.include_router(order_date_search_router)
app.include_router(cnr_search_router)


# Mount Frontend static files
PUBLIC_DIR = settings.PUBLIC_DIR

if PUBLIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = PUBLIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Frontend index.html not found"}
else:
    logger.warning(f"Public directory not found at {PUBLIC_DIR}")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
