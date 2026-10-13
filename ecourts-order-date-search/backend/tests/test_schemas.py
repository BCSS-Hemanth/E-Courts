"""
Unit tests for Pydantic schemas and request validations.
"""

import pytest
from pydantic import ValidationError
from app.schemas import SearchRequest, OrderDateCriteria, CaptchaSubmitRequest, CourtOrderResult


def test_valid_search_request():
    req = SearchRequest(
        state="  Delhi  ",
        district="  New Delhi  ",
        court_complex="  Patiala House Courts  ",
        order_date_criteria=OrderDateCriteria(
            from_date="01-01-2024",
            to_date="10-01-2024",
            order_type="interim"
        )
    )
    # Check whitespace trimming
    assert req.state == "Delhi"
    assert req.district == "New Delhi"
    assert req.court_complex == "Patiala House Courts"
    assert req.order_date_criteria.from_date == "01-01-2024"
    assert req.order_date_criteria.to_date == "10-01-2024"
    assert req.order_date_criteria.order_type == "interim"


def test_blank_location_fields_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(
            state="   ",
            district="New Delhi",
            court_complex="Patiala House Courts",
            order_date_criteria=OrderDateCriteria(
                from_date="01-01-2024",
                to_date="10-01-2024"
            )
        )


def test_invalid_date_format():
    # ISO YYYY-MM-DD should fail
    with pytest.raises(ValidationError):
        OrderDateCriteria(
            from_date="2024-01-01",
            to_date="10-01-2024"
        )

    # Invalid day
    with pytest.raises(ValidationError):
        OrderDateCriteria(
            from_date="32-01-2024",
            to_date="10-01-2024"
        )


def test_from_date_after_to_date_rejected():
    with pytest.raises(ValidationError) as exc_info:
        OrderDateCriteria(
            from_date="15-01-2024",
            to_date="10-01-2024"
        )
    assert "cannot be after To Date" in str(exc_info.value)


def test_order_type_options():
    crit1 = OrderDateCriteria(from_date="01-01-2024", to_date="05-01-2024", order_type="interim")
    assert crit1.order_type == "interim"

    crit2 = OrderDateCriteria(from_date="01-01-2024", to_date="05-01-2024", order_type="final")
    assert crit2.order_type == "final"

    crit3 = OrderDateCriteria(from_date="01-01-2024", to_date="05-01-2024", order_type="both")
    assert crit3.order_type == "both"

    with pytest.raises(ValidationError):
        OrderDateCriteria(from_date="01-01-2024", to_date="05-01-2024", order_type="unknown")


def test_captcha_submit_request():
    req = CaptchaSubmitRequest(captcha="  z75cmr  ")
    assert req.captcha == "z75cmr"

    with pytest.raises(ValidationError):
        CaptchaSubmitRequest(captcha="   ")


def test_court_order_result_null_handling():
    # Tests that missing fields return null (None) without crashing
    res = CourtOrderResult(sl_no=1)
    assert res.sl_no == 1
    assert res.case_number is None
    assert res.party_name is None
    assert res.order_url is None
