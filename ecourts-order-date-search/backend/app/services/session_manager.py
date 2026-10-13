"""
Temporary In-Memory Session Manager.
Strictly adheres to:
- No database or persistent storage (no SQLite, PostgreSQL, Redis, etc.)
- In-memory state only for active search/browser sessions
- Automatic cleanup of expired sessions and browser resources
"""

import asyncio
import time
import uuid
import logging
from typing import Dict, Optional, List, Any
from app.config import settings
from app.schemas import SearchRequest, SearchStatus, CourtOrderResult

logger = logging.getLogger(__name__)


class SearchSession:
    def __init__(self, search_id: str, request: SearchRequest):
        self.search_id: str = search_id
        self.request: SearchRequest = request
        self.status: SearchStatus = SearchStatus.RUNNING
        self.message: Optional[str] = "Search initiated. Initializing browser session..."
        self.error_code: Optional[str] = None
        self.captcha_image: Optional[str] = None
        self.captcha_event: asyncio.Event = asyncio.Event()
        self.captcha_answer: Optional[str] = None
        self.results: List[CourtOrderResult] = []
        self.total_count: int = 0
        self.cached_documents: Dict[str, Dict[str, Any]] = {}

        # Ephemeral Playwright objects
        self.playwright: Any = None
        self.browser: Any = None
        self.context: Any = None
        self.page: Any = None
        self.task: Optional[asyncio.Task] = None

        self.created_at: float = time.time()
        self.updated_at: float = time.time()

    def touch(self):
        self.updated_at = time.time()

    def is_expired(self) -> bool:
        return (time.time() - self.updated_at) > settings.SESSION_TIMEOUT_SECONDS

    def store_document(self, sl_no: str, doc_data: Dict[str, Any]):
        """Store official PDF document data in memory."""
        self.cached_documents[str(sl_no)] = doc_data
        self.touch()

    def get_document(self, sl_no: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored document data."""
        self.touch()
        return self.cached_documents.get(str(sl_no))

    async def release_resources(self):
        """Safely release Playwright page, context, and browser."""
        try:
            if self.page:
                try:
                    await self.page.close()
                except Exception as e:
                    logger.debug(f"Error closing page for {self.search_id}: {e}")
                self.page = None

            if self.context:
                try:
                    await self.context.close()
                except Exception as e:
                    logger.debug(f"Error closing context for {self.search_id}: {e}")
                self.context = None

            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    logger.debug(f"Error closing browser for {self.search_id}: {e}")
                self.browser = None

            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    logger.debug(f"Error stopping playwright for {self.search_id}: {e}")
                self.playwright = None

        except Exception as e:
            logger.warning(f"Error during resource release for {self.search_id}: {e}")


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, SearchSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, request: SearchRequest) -> SearchSession:
        await self.cleanup_expired_sessions()

        if len(self._sessions) >= settings.MAX_CONCURRENT_SESSIONS:
            raise RuntimeError("Server is at maximum concurrent search capacity. Please try again shortly.")

        search_id = str(uuid.uuid4())
        session = SearchSession(search_id=search_id, request=request)
        async with self._lock:
            self._sessions[search_id] = session
        logger.info(f"Created session {search_id}")
        return session

    async def get_session(self, search_id: str) -> Optional[SearchSession]:
        session = self._sessions.get(search_id)
        if not session:
            return None
        if session.is_expired() and session.status not in (SearchStatus.COMPLETED, SearchStatus.NO_RESULTS):
            session.status = SearchStatus.EXPIRED
            session.message = "Session expired due to inactivity."
            await session.release_resources()
        return session

    async def update_status(
        self,
        search_id: str,
        status: SearchStatus,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        captcha_image: Optional[str] = None,
        results: Optional[List[CourtOrderResult]] = None
    ):
        session = self._sessions.get(search_id)
        if not session:
            return

        session.status = status
        if message is not None:
            session.message = message
        if error_code is not None:
            session.error_code = error_code
        if captcha_image is not None:
            session.captcha_image = captcha_image
        if results is not None:
            session.results = results
            session.total_count = len(results)

        session.touch()
        logger.info(f"Session {search_id} updated to status {status.value}")

        # If terminal state, release browser resources immediately
        if status in (SearchStatus.COMPLETED, SearchStatus.NO_RESULTS, SearchStatus.FAILED, SearchStatus.CANCELLED, SearchStatus.EXPIRED):
            await session.release_resources()

    async def submit_captcha(self, search_id: str, captcha_answer: str) -> bool:
        session = await self.get_session(search_id)
        if not session:
            return False
        if session.status != SearchStatus.CAPTCHA_REQUIRED:
            return False

        session.captcha_answer = captcha_answer
        session.status = SearchStatus.RUNNING
        session.message = "Verifying CAPTCHA and submitting search..."
        session.touch()
        # Notify the waiting scraper coroutine
        session.captcha_event.set()
        return True

    async def cancel_session(self, search_id: str) -> bool:
        session = self._sessions.get(search_id)
        if not session:
            return False

        session.status = SearchStatus.CANCELLED
        session.message = "Search cancelled by user."
        session.touch()

        if session.task and not session.task.done():
            session.task.cancel()

        session.captcha_event.set()
        await session.release_resources()
        return True

    async def cleanup_expired_sessions(self):
        """Remove old sessions to ensure no memory accumulation."""
        now = time.time()
        expired_ids = []
        for sid, session in list(self._sessions.items()):
            if (now - session.updated_at) > settings.SESSION_TIMEOUT_SECONDS:
                expired_ids.append(sid)

        for sid in expired_ids:
            session = self._sessions.pop(sid, None)
            if session:
                await session.release_resources()
                logger.debug(f"Cleaned up expired session {sid}")

    async def get_document(self, search_id: str, sl_no: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored official document for a search session."""
        session = await self.get_session(search_id)
        if not session:
            return None
        return session.get_document(sl_no)

    def active_session_count(self) -> int:
        return len(self._sessions)


# Global singleton instance
session_manager = SessionManager()
