"""
Integration tests for FastAPI REST endpoints using httpx AsyncClient.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.schemas import SearchStatus


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "active_sessions" in data


@pytest.mark.asyncio
async def test_search_api_validation_failure():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing state
        response = await client.post("/api/search", json={
            "state": "",
            "district": "New Delhi",
            "court_complex": "Patiala House Courts",
            "order_date_criteria": {
                "from_date": "01-01-2024",
                "to_date": "10-01-2024",
                "order_type": "interim"
            }
        })
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_api_initiation_and_cancellation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Submit valid search
        response = await client.post("/api/search", json={
            "state": "Delhi",
            "district": "New Delhi",
            "court_complex": "Patiala House Courts",
            "order_date_criteria": {
                "from_date": "01-01-2024",
                "to_date": "10-01-2024",
                "order_type": "interim"
            }
        })
        assert response.status_code == 202
        data = response.json()
        search_id = data["search_id"]
        assert search_id is not None
        assert data["status"] == "running"

        # Check status
        status_resp = await client.get(f"/api/search/{search_id}")
        assert status_resp.status_code == 200

        # Cancel search
        cancel_resp = await client.post(f"/api/search/{search_id}/cancel")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_non_existent_search_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/search/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_document_endpoint_with_cached_doc():
    from app.services.session_manager import session_manager
    from app.schemas import SearchRequest, OrderDateCriteria
    
    req = SearchRequest(
        state="Delhi",
        district="New Delhi",
        court_complex="Patiala House Courts",
        order_date_criteria=OrderDateCriteria(
            from_date="01-01-2024",
            to_date="10-01-2024",
            order_type="interim"
        )
    )
    session = await session_manager.create_session(req)
    # Store a dummy PDF
    session.store_document("1", {
        "content": b"%PDF-1.4 test pdf content",
        "filename": "test_order.pdf",
        "content_type": "application/pdf"
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Non-existent session
        res_404 = await client.get("/api/document/00000000-0000-0000-0000-000000000000/1")
        assert res_404.status_code == 404

        # Valid document
        res_doc = await client.get(f"/api/document/{session.search_id}/1")
        assert res_doc.status_code == 200
        assert res_doc.headers["content-type"] == "application/pdf"
        assert res_doc.content.startswith(b"%PDF-1.4")
