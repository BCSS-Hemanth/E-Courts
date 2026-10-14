"""
Pydantic data models and schemas for eCourts Order Date Search.
"""

from enum import Enum
from typing import List, Optional, Literal
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
