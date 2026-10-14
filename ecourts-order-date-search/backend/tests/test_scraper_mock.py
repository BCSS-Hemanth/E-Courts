"""
Unit tests for scraper logic, option matching, captcha generation, and HTML parsing.
"""

import pytest
import asyncio
from bs4 import BeautifulSoup
from app.schemas import SearchRequest, OrderDateCriteria, SearchStatus
from app.services.session_manager import session_manager
from app.services.ecourts_scraper import (
    match_option,
    normalize_text,
    generate_mock_captcha,
    ecourts_scraper
)


def test_normalize_text():
    assert normalize_text("  Delhi  ") == "delhi"
    assert normalize_text("New   Delhi") == "new delhi"
    assert normalize_text("MAHARASHTRA") == "maharashtra"


def test_match_option_exact():
    options = [
        {"value": "0", "text": "-- Select State --"},
        {"value": "1", "text": "Delhi"},
        {"value": "2", "text": "Maharashtra"},
        {"value": "3", "text": "Karnataka"}
    ]

    val, err = match_option("Delhi", options)
    assert val == "1"
    assert err is None

    # Capitalization & whitespace tolerance
    val, err = match_option("  delhi  ", options)
    assert val == "1"
    assert err is None


def test_match_option_unmatched():
    options = [
        {"value": "1", "text": "Delhi"},
        {"value": "2", "text": "Maharashtra"}
    ]

    val, err = match_option("Goa", options)
    assert val is None
    assert "Could not find 'Goa'" in err


def test_match_option_ambiguous():
    options = [
        {"value": "1", "text": "North Court Complex"},
        {"value": "2", "text": "South Court Complex"}
    ]

    val, err = match_option("Court Complex", options)
    assert val is None
    assert "Ambiguous input" in err


def test_match_option_aliases():
    options = [
        {"value": "1", "text": "Telangana"},
        {"value": "2", "text": "Andhra Pradesh"},
        {"value": "3", "text": "Bengaluru Urban"}
    ]

    # Test abbreviation alias TG and TS
    val, err = match_option("TG", options)
    assert val == "1"
    assert err is None

    val, err = match_option("ts", options)
    assert val == "1"
    assert err is None

    # Test colloquial city alias Bangalore
    val, err = match_option("Bangalore", options)
    assert val == "3"
    assert err is None


def test_match_option_telangana_locations():
    dist_options = [
        {"value": "1", "text": "Adilabad"},
        {"value": "2", "text": "Hyderabad CCC"},
        {"value": "9", "text": "Rangareddy"},
        {"value": "23", "text": "Medchal Malkajgiri"}
    ]

    # Spaced "Ranga Reddy" matches "Rangareddy"
    val, err = match_option("Ranga Reddy", dist_options)
    assert val == "9"
    assert err is None

    # Hyphenated "Medchal-Malkajgiri" matches "Medchal Malkajgiri"
    val, err = match_option("Medchal-Malkajgiri", dist_options)
    assert val == "23"
    assert err is None

    # "Hyderabad" matches "Hyderabad CCC"
    val, err = match_option("Hyderabad", dist_options)
    assert val == "2"
    assert err is None

    # Test Court Complex fuzzy keyword matching
    complex_options = [
        {"value": "1290112@1,2,3,5,6,31,43@N", "text": "Rangareddy, PDJ Court Complex"},
        {"value": "1290115@36,37,38@N", "text": "Kukatpally, ADJ-cum-Family Court"},
        {"value": "1290106@19,32,41@N", "text": "Rajendra Nagar, ADJ Court Complex"}
    ]

    val, err = match_option("Kukatpally Court Complex", complex_options)
    assert val == "1290115@36,37,38@N"
    assert err is None



def test_generate_mock_captcha():
    text, b64 = generate_mock_captcha("z75cmr")
    assert text == "z75cmr"
    assert b64.startswith("data:image/png;base64,")
    assert len(b64) > 100


def test_parse_live_results_table():
    html_sample = """
    <table id="dispTable">
        <thead>
            <tr>
                <th>Sl</th><th>Case Type</th><th>Case Number</th><th>Party Name</th><th>Order Date</th><th>Court</th><th>Order</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>1</td>
                <td>Criminal Case</td>
                <td>CC/101/2024</td>
                <td>State vs John Doe</td>
                <td>05-01-2024</td>
                <td>Court of CMM</td>
                <td><a href="/ecourtindia_v6/view_pdf.php?id=123">View Order</a></td>
            </tr>
            <tr>
                <td>2</td>
                <td>Civil Suit</td>
                <td>CS/202/2024</td>
                <td>ABC Corp vs XYZ Ltd</td>
                <td>08-01-2024</td>
                <td>Court of ADJ</td>
                <td><a href="javascript:void(0);">No Link</a></td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html_sample, "html.parser")
    results = ecourts_scraper._parse_live_results_table(soup, "https://services.ecourts.gov.in")
    assert len(results) == 2
    assert results[0].case_number == "CC/101/2024"
    assert results[0].party_name == "State vs John Doe"
    assert results[0].order_url == "https://services.ecourts.gov.in/ecourtindia_v6/view_pdf.php?id=123"

    # Second row javascript:void link should be treated as None
    assert results[1].order_url is None


@pytest.mark.asyncio
async def test_mock_search_workflow():
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

    # Launch mock search
    task = asyncio.create_task(ecourts_scraper._run_mock_search(session))

    # Wait until it reaches CAPTCHA_REQUIRED
    for _ in range(30):
        await asyncio.sleep(0.1)
        if session.status == SearchStatus.CAPTCHA_REQUIRED:
            break

    assert session.status == SearchStatus.CAPTCHA_REQUIRED
    assert session.captcha_image is not None

    # Submit valid captcha
    await session_manager.submit_captcha(session.search_id, "z75cmr")

    # Await search completion
    await task
    assert session.status == SearchStatus.COMPLETED
    assert len(session.results) > 0
    assert session.results[0].court_name is not None


@pytest.mark.asyncio
async def test_telangana_search_workflow():
    """Verify that Telangana, its districts, and court complexes work end-to-end."""
    req = SearchRequest(
        state="Telangana",
        district="Hyderabad",
        court_complex="Nampally Criminal Courts Complex",
        order_date_criteria=OrderDateCriteria(
            from_date="05-02-2024",
            to_date="15-02-2024",
            order_type="final"
        )
    )
    session = await session_manager.create_session(req)

    # Launch mock search
    task = asyncio.create_task(ecourts_scraper._run_mock_search(session))

    # Wait until it reaches CAPTCHA_REQUIRED
    for _ in range(30):
        await asyncio.sleep(0.1)
        if session.status == SearchStatus.CAPTCHA_REQUIRED:
            break

    assert session.status == SearchStatus.CAPTCHA_REQUIRED
    assert session.captcha_image is not None

    # Submit valid captcha
    await session_manager.submit_captcha(session.search_id, "z75cmr")

    # Await search completion
    await task
    assert session.status == SearchStatus.COMPLETED
    assert len(session.results) > 0
    assert "Nampally" in session.results[0].court_name
    assert session.results[0].order_url == f"/api/document/{session.search_id}/1"
    doc = session.get_document("1")
    assert doc is not None
    assert doc["content"].startswith(b"%PDF-1.4")
