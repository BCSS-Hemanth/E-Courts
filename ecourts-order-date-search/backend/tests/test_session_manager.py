"""
Unit tests for the In-Memory Session Manager.
"""

import pytest
import asyncio
from app.schemas import SearchRequest, OrderDateCriteria, SearchStatus
from app.services.session_manager import SessionManager


@pytest.fixture
def manager():
    return SessionManager()


@pytest.fixture
def sample_request():
    return SearchRequest(
        state="Delhi",
        district="New Delhi",
        court_complex="Patiala House Courts",
        order_date_criteria=OrderDateCriteria(
            from_date="01-01-2024",
            to_date="10-01-2024",
            order_type="interim"
        )
    )


@pytest.mark.asyncio
async def test_session_lifecycle(manager, sample_request):
    session = await manager.create_session(sample_request)
    assert session.search_id is not None
    assert session.status == SearchStatus.RUNNING

    # Fetch session
    fetched = await manager.get_session(session.search_id)
    assert fetched is not None
    assert fetched.search_id == session.search_id

    # Update status to CAPTCHA_REQUIRED
    await manager.update_status(
        session.search_id,
        SearchStatus.CAPTCHA_REQUIRED,
        message="Manual captcha needed",
        captcha_image="data:image/png;base64,mock"
    )
    assert session.status == SearchStatus.CAPTCHA_REQUIRED
    assert session.captcha_image == "data:image/png;base64,mock"

    # Submit captcha
    submitted = await manager.submit_captcha(session.search_id, "z75cmr")
    assert submitted is True
    assert session.captcha_answer == "z75cmr"
    assert session.captcha_event.is_set()

    # Cancel session
    cancelled = await manager.cancel_session(session.search_id)
    assert cancelled is True
    assert session.status == SearchStatus.CANCELLED


@pytest.mark.asyncio
async def test_non_existent_session(manager):
    res = await manager.get_session("non-existent-uuid")
    assert res is None

    cancel_res = await manager.cancel_session("non-existent-uuid")
    assert cancel_res is False


@pytest.mark.asyncio
async def test_session_expiration(manager, sample_request):
    session = await manager.create_session(sample_request)
    # Simulate time lapse by artificially setting updated_at far in past
    session.updated_at = session.updated_at - 400

    fetched = await manager.get_session(session.search_id)
    assert fetched.status == SearchStatus.EXPIRED
