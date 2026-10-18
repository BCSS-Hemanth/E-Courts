"""
Root launcher script for eCourts Order Date Search.
Runs the FastAPI server with both backend API and frontend static assets.
"""

import sys
import asyncio
from pathlib import Path

# ProactorEventLoop is default on Windows since Python 3.8; only set explicitly on legacy Python versions (<3.14)
if sys.platform == "win32" and sys.version_info < (3, 14):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 65)
    print("  eCourts Order Date Search Portal")
    print("  Local URL: http://127.0.0.1:8000")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 65 + "\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
