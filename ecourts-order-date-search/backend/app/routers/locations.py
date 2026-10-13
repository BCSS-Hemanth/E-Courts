"""
Location router providing State, District, and Court Complex endpoints for dropdowns.
"""

from typing import List, Dict
from fastapi import APIRouter, Query, HTTPException
from app.services.location_service import location_service

router = APIRouter(prefix="/api/locations", tags=["Locations"])


@router.get("/states")
async def get_states() -> List[Dict[str, str]]:
    """Return all available States and Union Territories with official eCourts codes."""
    return location_service.get_states()


@router.get("/districts")
async def get_districts(state_code: str = Query(..., description="Numeric code of the selected state")) -> List[Dict[str, str]]:
    """Return all districts for the given state code."""
    districts = await location_service.get_districts(state_code)
    return districts


@router.get("/complexes")
async def get_complexes(
    state_code: str = Query(..., description="Numeric code of the selected state"),
    dist_code: str = Query(..., description="Numeric code of the selected district")
) -> List[Dict[str, str]]:
    """Return all court complexes for the given state and district codes."""
    complexes = await location_service.get_complexes(state_code, dist_code)
    return complexes
