"""
Search router exposing REST API endpoints for eCourts Order Date Search.
Endpoints:
- GET /api/health
- POST /api/search
- GET /api/search/{search_id}
- POST /api/search/{search_id}/captcha
- POST /api/search/{search_id}/cancel
- GET /api/document/{search_id}/{sl_no}
- GET /api/locations
- GET /api/locations/states
- GET /api/locations/districts
- GET /api/locations/complexes
"""

import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, status, Response, Query
from fastapi.responses import RedirectResponse
import logging

from app.schemas import (
    SearchRequest,
    SearchStatusResponse,
    CaptchaSubmitRequest,
    HealthResponse,
    SearchStatus
)
from app.search_session_manager import session_manager
from app.ecourts_scraper import ecourts_scraper
from app.court_location_service import location_service
from app.pdf_report_generator import generate_court_order_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Court Order Date Search"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Return backend health status and active session count."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        active_sessions=session_manager.active_session_count()
    )


@router.post("/search", response_model=SearchStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def initiate_search(request: SearchRequest):
    """
    Start an Order Date search session.
    1. Validates inputs via Pydantic.
    2. Initializes in-memory session.
    3. Triggers asynchronous browser scraping task.
    4. Returns temporary search_id and status 'running'.
    """
    try:
        session = await session_manager.create_session(request)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    # Launch scraping in background task
    task = asyncio.create_task(ecourts_scraper.execute_search(session.search_id))
    session.task = task

    return SearchStatusResponse(
        search_id=session.search_id,
        status=session.status,
        message=session.message,
        results=[],
        total_count=0,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.get("/search/{search_id}", response_model=SearchStatusResponse)
async def get_search_status(search_id: str):
    """
    Retrieve current status and (when complete) results of an active search session.
    """
    session = await session_manager.get_session(search_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search session '{search_id}' not found or has expired."
        )

    return SearchStatusResponse(
        search_id=session.search_id,
        status=session.status,
        message=session.message,
        error_code=session.error_code,
        captcha_image=session.captcha_image if session.status == SearchStatus.CAPTCHA_REQUIRED else None,
        results=session.results,
        total_count=session.total_count,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.post("/search/{search_id}/captcha", response_model=SearchStatusResponse)
async def submit_captcha(search_id: str, payload: CaptchaSubmitRequest):
    """
    Accept manually entered CAPTCHA challenge answer and resume the active search.
    """
    session = await session_manager.get_session(search_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search session '{search_id}' not found."
        )

    if session.status != SearchStatus.CAPTCHA_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is in '{session.status.value}' state, not awaiting CAPTCHA."
        )

    success = await session_manager.submit_captcha(search_id, payload.captcha)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit CAPTCHA to active browser session."
        )

    return SearchStatusResponse(
        search_id=session.search_id,
        status=session.status,
        message="CAPTCHA accepted. Proceeding with court order query...",
        results=[],
        total_count=0,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.post("/search/{search_id}/cancel", response_model=SearchStatusResponse)
async def cancel_search(search_id: str):
    """
    Cancel active search and immediately release all temporary browser resources.
    """
    session = await session_manager.get_session(search_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search session '{search_id}' not found."
        )

    await session_manager.cancel_session(search_id)

    return SearchStatusResponse(
        search_id=session.search_id,
        status=SearchStatus.CANCELLED,
        message="Search cancelled by user.",
        results=[],
        total_count=0,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.get("/document/{search_id}/{sl_no}")
async def get_court_order_document(search_id: str, sl_no: str):
    """
    Serve the authentic official court order / decree PDF document.
    Streams directly from in-memory session cache or proxies the official document.
    """
    session = await session_manager.get_session(search_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search session '{search_id}' has expired or is invalid."
        )

    # Check cached documents in session
    doc = session.get_document(sl_no)
    if doc and "content" in doc and doc["content"]:
        filename = doc.get("filename", f"court_order_{sl_no}.pdf")
        return Response(
            content=doc["content"],
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )

    # If an official external URL was resolved, redirect to it
    if doc and doc.get("official_url"):
        return RedirectResponse(url=doc["official_url"])

    # Fallback: check matching result in session results
    target_result = None
    for res in session.results:
        if str(res.sl_no) == str(sl_no):
            target_result = res
            break

    if target_result:
        pdf_bytes = generate_court_order_pdf(
            court_name=target_result.court_name or "District Court",
            case_number=target_result.case_number or "N/A",
            case_type=target_result.case_type or "Civil/Criminal",
            parties=target_result.party_name or "N/A",
            order_date=target_result.order_date or "N/A",
            order_type=target_result.order_type or "Court Order"
        )
        safe_cno = (target_result.case_number or f"order_{sl_no}").replace("/", "_").replace(" ", "_")
        filename = f"{safe_cno}_{target_result.order_type or 'order'}.pdf"
        session.store_document(sl_no, {"content": pdf_bytes, "filename": filename, "content_type": "application/pdf"})
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Court order document #{sl_no} not found for session '{search_id}'."
    )


# ---------------------------------------------------------------------------
# Location Directory Endpoints (Cached from eCourts)
# ---------------------------------------------------------------------------

@router.get("/locations")
async def get_all_locations():
    """Return all cached States, Districts, and Court Complexes."""
    return location_service.get_all()


@router.get("/locations/states")
async def get_states():
    """Return list of available Indian States & Union Territories."""
    return location_service.get_states()


@router.get("/locations/districts")
async def get_districts(
    state: str = Query(None, description="State name"),
    state_code: str = Query(None, description="State code")
):
    """Return list of districts for a selected state name or state code."""
    param = state or state_code
    if not param:
        raise HTTPException(status_code=400, detail="state or state_code query parameter is required")
    return await location_service.get_districts(param)


@router.get("/locations/complexes")
async def get_court_complexes(
    state: str = Query(None, description="State name"),
    state_code: str = Query(None, description="State code"),
    district: str = Query(None, description="District name"),
    dist_code: str = Query(None, description="District code")
):
    """Return list of court complexes for a selected district."""
    st = state or state_code
    dt = district or dist_code
    if not st or not dt:
        raise HTTPException(status_code=400, detail="state and district parameters are required")
    return await location_service.get_court_complexes(st, dt)
