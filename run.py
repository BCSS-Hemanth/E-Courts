"""
Root launcher script for eCourts Order Date Search.
Runs the FastAPI server with both backend API and frontend static assets.
"""

import sys
import asyncio
from pathlib import Path

# Ensure Windows ProactorEventLoop is used for Playwright subprocesses
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Add backend directory to Python path
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "ecourts-order-date-search" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 65)
    print("  eCourts Order Date Search Portal")
    print("  Local URL: http://127.0.0.1:8000")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 65 + "\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
