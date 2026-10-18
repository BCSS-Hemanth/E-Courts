"""
Integration tests for CNR Search REST API endpoints and scraper service.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.schemas import CnrSearchRequest, SearchStatus
from app.search_session_manager import session_manager
from app.cnr_scraper import cnr_scraper


@pytest.mark.asyncio
async def test_cnr_search_validation_failure():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid length (15 chars)
        res1 = await client.post("/api/cnr-search", json={"cnr_number": "MHAU01999999201"})
        assert res1.status_code == 422

        # Invalid characters (contains special chars)
        res2 = await client.post("/api/cnr-search", json={"cnr_number": "MHAU01999999201#"})
        assert res2.status_code == 422

        # Blank
        res3 = await client.post("/api/cnr-search", json={"cnr_number": ""})
        assert res3.status_code == 422


@pytest.mark.asyncio
async def test_cnr_search_initiation_and_cancellation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Initiate valid search
        res = await client.post("/api/cnr-search", json={"cnr_number": "MHAU019999992015"})
        assert res.status_code == 202
        data = res.json()
        search_id = data["search_id"]
        assert search_id is not None
        assert data["status"] == "running"

        # Check status
        status_res = await client.get(f"/api/cnr-search/{search_id}")
        assert status_res.status_code == 200

        # Cancel search
        cancel_res = await client.post(f"/api/cnr-search/{search_id}/cancel")
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cnr_non_existent_search_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/cnr-search/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_cnr_document_endpoint():
    req = CnrSearchRequest(cnr_number="MHAU019999992015")
    session = await session_manager.create_session(req)

    # Store a dummy PDF
    session.store_document("1", {
        "content": b"%PDF-1.4 official cnr order pdf",
        "filename": "cnr_order_1.pdf",
        "content_type": "application/pdf"
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 404 on non-existent
        res_404 = await client.get("/api/cnr-document/00000000-0000-0000-0000-000000000000/1")
        assert res_404.status_code == 404

        # Valid document retrieval
        res_doc = await client.get(f"/api/cnr-document/{session.search_id}/1")
        assert res_doc.status_code == 200
        assert res_doc.headers["content-type"] == "application/pdf"
        assert res_doc.content.startswith(b"%PDF-1.4")


@pytest.mark.asyncio
async def test_cnr_mock_simulation_execution():
    req = CnrSearchRequest(cnr_number="DLND010012342021")
    session = await session_manager.create_session(req)

    await cnr_scraper._run_mock_cnr_search(session)

    assert session.status == SearchStatus.COMPLETED
    assert session.case_details is not None
    assert session.case_details.cnr_number == "DLND010012342021"
    assert session.case_details.state_name == "Delhi"
    assert len(session.case_details.orders) > 0

    # Verify order document was stored and is valid PDF
    doc = session.get_document("1")
    assert doc is not None
    assert doc["content"].startswith(b"%PDF")


@pytest.mark.asyncio
async def test_cnr_tshm_authentic_business_records_and_endpoint():
    req = CnrSearchRequest(cnr_number="TSHM010063492024")
    session = await session_manager.create_session(req)

    await cnr_scraper._run_mock_cnr_search(session)

    assert session.status == SearchStatus.COMPLETED
    assert session.case_details is not None
    assert session.case_details.business_records is not None
    assert len(session.case_details.business_records) == 15

    # Check authentic content on 20-03-2025 (acquittal judgment note)
    rec_20_03 = session.case_details.business_records.get("20-03-2025")
    assert rec_20_03 is not None
    assert "Daily Status" in rec_20_03
    assert "ACQUITTAL" in rec_20_03
    assert "VIII Addl. Chief Metropolitan Magistrate" in rec_20_03

    # Check authentic content on 17-03-2025 (magistrate proceedings note)
    rec_17_03 = session.case_details.business_records.get("17-03-2025")
    assert rec_17_03 is not None
    assert "Accused is called present" in rec_17_03
    assert "313 Cr.P.C" in rec_17_03

    # Test API endpoint GET /api/cnr-business/{search_id}/{date}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/cnr-business/{session.search_id}/20-03-2025")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == 1
        assert "Daily Status" in data["data_list"]
        assert "ACQUITTAL" in data["data_list"]

        # 404 on non-existent date
        res_404 = await client.get(f"/api/cnr-business/{session.search_id}/01-01-1999")
        assert res_404.status_code == 404

        # Test judgment document endpoint for TSHM010063492024
        res_doc = await client.get(f"/api/cnr-document/{session.search_id}/1")
        assert res_doc.status_code == 200
        assert res_doc.headers["content-type"] == "application/pdf"
        assert res_doc.content.startswith(b"%PDF")
        assert len(res_doc.content) > 10000

