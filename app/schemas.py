"""
Pydantic data models and schemas for eCourts Order Date Search.
"""

import re
from enum import Enum
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class OrderTypeEnum(str, Enum):
    INTERIM = "interim"
    FINAL = "final"
    BOTH = "both"


class SearchStatus(str, Enum):
    RUNNING = "running"
    CAPTCHA_REQUIRED = "captcha_required"
    COMPLETED = "completed"
    NO_RESULTS = "no_results"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class OrderDateCriteria(BaseModel):
    """
    Search criteria strictly matching the official eCourts Order Date tab:
    - *From Date (DD-MM-YYYY)
    - *To Date (DD-MM-YYYY)
    - Order Type: Interim Orders | Final Orders | Both
    """
    from_date: str = Field(
        ...,
        description="Start date in DD-MM-YYYY format",
        examples=["01-01-2024"]
    )
    to_date: str = Field(
        ...,
        description="End date in DD-MM-YYYY format",
        examples=["15-01-2024"]
    )
    order_type: Literal["interim", "final", "both"] = Field(
        default="interim",
        description="Order type: 'interim', 'final', or 'both'"
    )

    @field_validator("from_date", "to_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        v = v.strip()
        try:
            # Parse DD-MM-YYYY
            parsed = datetime.strptime(v, "%d-%m-%Y")
        except ValueError:
            raise ValueError(f"Invalid date format '{v}'. Expected DD-MM-YYYY (e.g. 05-01-2024).")
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "OrderDateCriteria":
        d_from = datetime.strptime(self.from_date, "%d-%m-%Y")
        d_to = datetime.strptime(self.to_date, "%d-%m-%Y")
        if d_from > d_to:
            raise ValueError(f"From Date ({self.from_date}) cannot be after To Date ({self.to_date}).")
        return self


class SearchRequest(BaseModel):
    """
    User search submission.
    State, District, and Court Complex selected via dropdowns with optional exact codes.
    """
    state: str = Field(
        ...,
        min_length=1,
        description="State name (e.g., Telangana, Delhi, Maharashtra)",
        examples=["Telangana"]
    )
    district: str = Field(
        ...,
        min_length=1,
        description="District name (e.g., Rangareddy, New Delhi, Mumbai)",
        examples=["Rangareddy"]
    )
    court_complex: str = Field(
        ...,
        min_length=1,
        description="Court Complex name (e.g., Kukatpally, ADJ-cum-Family Court)",
        examples=["Kukatpally, ADJ-cum-Family Court"]
    )
    state_code: Optional[str] = Field(
        default=None,
        description="Official eCourts state code (e.g. '29')"
    )
    district_code: Optional[str] = Field(
        default=None,
        description="Official eCourts district code (e.g. '9')"
    )
    court_complex_code: Optional[str] = Field(
        default=None,
        description="Official eCourts complex code (e.g. '1290115@36,37,38@N')"
    )
    order_date_criteria: OrderDateCriteria

    @field_validator("state", "district", "court_complex")
    @classmethod
    def clean_text_inputs(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Location fields cannot be blank or whitespace-only.")
        return cleaned


class CaptchaSubmitRequest(BaseModel):
    """Manual CAPTCHA submission by the user."""
    captcha: str = Field(
        ...,
        min_length=1,
        description="User-entered CAPTCHA text challenge answer",
        examples=["z75cmr"]
    )

    @field_validator("captcha")
    @classmethod
    def clean_captcha(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("CAPTCHA text cannot be empty.")
        return cleaned


class CourtOrderResult(BaseModel):
    """
    Extracted court order item.
    Never fabricates values; returns null for unpopulated attributes.
    """
    sl_no: int = Field(..., description="Serial sequence number in results")
    case_type: Optional[str] = Field(None, description="Case Type (e.g. CC, CS, BAIL APPLN)")
    case_number: Optional[str] = Field(None, description="Case Number / Registration Number")
    party_name: Optional[str] = Field(None, description="Petitioner vs Respondent")
    order_date: Optional[str] = Field(None, description="Order Date (DD-MM-YYYY)")
    order_number: Optional[str] = Field(None, description="Order / Item sequence number")
    order_type: Optional[str] = Field(None, description="Interim or Final order designation")
    court_name: Optional[str] = Field(None, description="Presiding Court / Judge designation")
    order_url: Optional[str] = Field(
        None,
        description="Valid official document URL (opened directly in new tab)"
    )


class SearchStatusResponse(BaseModel):
    """
    Real-time status of a search operation.
    """
    search_id: str
    status: SearchStatus
    message: Optional[str] = None
    error_code: Optional[str] = None
    captcha_image: Optional[str] = None  # Base64 data URL
    results: List[CourtOrderResult] = []
    total_count: int = 0
    created_at: float
    updated_at: float


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"
    active_sessions: int


# ---------------------------------------------------------------------------
# CNR Search Schemas
# ---------------------------------------------------------------------------

class CnrSearchRequest(BaseModel):
    """
    Search request for case retrieval via 16-digit CNR number.
    Format: 2 state letters + 2 district letters + 6 case/establishment digits + 4 year digits.
    Example: MHAU019999992015
    """
    cnr_number: str = Field(
        ...,
        min_length=16,
        max_length=16,
        description="16-character alphanumeric Case Navigation Record (CNR) number",
        examples=["MHAU019999992015"]
    )

    @field_validator("cnr_number")
    @classmethod
    def validate_cnr(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z0-9]{16}$", v):
            raise ValueError("CNR number must be exactly 16 alphanumeric characters (e.g. MHAU019999992015).")
        return v


class CnrCaseDetails(BaseModel):
    """
    Structured judicial case details extracted from CNR lookup.
    """
    cnr_number: str = Field(..., description="16-character alphanumeric CNR identifier")
    case_type: Optional[str] = Field(None, description="Case classification (e.g. Regular Civil Suit, Criminal Case)")
    filing_number: Optional[str] = Field(None, description="Official court filing sequence")
    filing_date: Optional[str] = Field(None, description="Filing registration date (DD-MM-YYYY)")
    registration_number: Optional[str] = Field(None, description="Case registration number")
    registration_date: Optional[str] = Field(None, description="Registration date (DD-MM-YYYY)")
    case_status: Optional[str] = Field(None, description="Status of the case: PENDING or DISPOSED")
    nature_of_disposal: Optional[str] = Field(None, description="Disposal reason if disposed (e.g. Contested Dismissed, Decided)")
    subordinate_court: Optional[str] = Field(None, description="Lower court trial details if appeal")
    first_hearing_date: Optional[str] = Field(None, description="First hearing date (DD-MM-YYYY)")
    decision_date: Optional[str] = Field(None, description="Final decision or disposal date (DD-MM-YYYY)")
    next_hearing_date: Optional[str] = Field(None, description="Upcoming scheduled hearing date (DD-MM-YYYY)")
    case_stage: Optional[str] = Field(None, description="Current procedural stage")
    court_number_judge: Optional[str] = Field(None, description="Presiding judge designation and courtroom")
    petitioner_and_advocate: Optional[str] = Field(None, description="Petitioner(s) and legal counsel")
    respondent_and_advocate: Optional[str] = Field(None, description="Respondent(s) and legal counsel")
    court_name: Optional[str] = Field(None, description="Court Complex / Establishment")
    district_name: Optional[str] = Field(None, description="Judicial District")
    state_name: Optional[str] = Field(None, description="State / Union Territory")
    acts: List[Dict[str, str]] = Field(default_factory=list, description="Acts and sections involved")
    fir_details: Optional[Dict[str, Any]] = Field(default=None, description="FIR details: Police station, FIR No, Year")
    split_case_details: Optional[str] = Field(default=None, description="Split case or linked case numbers")
    history_of_hearings: List[Dict[str, Any]] = Field(default_factory=list, description="Historical hearing timeline")
    orders: List[CourtOrderResult] = Field(default_factory=list, description="All associated orders and judgments")
    raw_html: Optional[str] = Field(default=None, description="Exact raw HTML as rendered on official eCourts website")
    business_records: Dict[str, str] = Field(default_factory=dict, description="Authentic official HTML for each Case History hearing date")


class CnrSearchStatusResponse(BaseModel):
    """
    Real-time status response for CNR search sessions.
    """
    search_id: str
    status: SearchStatus
    message: Optional[str] = None
    error_code: Optional[str] = None
    captcha_image: Optional[str] = None
    case_details: Optional[CnrCaseDetails] = None
    raw_html: Optional[str] = None
    orders: List[CourtOrderResult] = []
    total_count: int = 0
    created_at: float
    updated_at: float

