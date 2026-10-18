"""
Location Service for eCourts Order Date Search.
Provides State, District, and Court Complex directory data cached locally
to minimize hits to the official eCourts government portal.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.ecourts_scraper import MOCK_LOCATION_DB, normalize_text, canonical_key

APP_DIR = Path(__file__).resolve().parent
DATA_FILE_PRIMARY = APP_DIR / "data" / "court_locations.json"
DATA_FILE_SECONDARY = APP_DIR / "court_locations.json"
CACHE_FILE = APP_DIR / "locations_cache.json"


class LocationService:
    def __init__(self):
        self._cached_data: Optional[Dict[str, Any]] = None

    def load_data(self) -> Dict[str, Any]:
        """Load and merge local JSON cache with built-in reference database."""
        if self._cached_data and len(self._cached_data.get("states", [])) > 0:
            return self._cached_data

        target_file = DATA_FILE_PRIMARY if DATA_FILE_PRIMARY.exists() else DATA_FILE_SECONDARY

        if target_file.exists():
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    states = file_data.get("states", [])
                    if states and len(states) >= 36:
                        # Full authentic directory loaded
                        sorted_states = sorted(states, key=lambda s: s["state_name"])
                        self._cached_data = {"states": sorted_states}
                        return self._cached_data
            except Exception as e:
                print(f"Warning: Failed to load {target_file}: {e}")

        # Fallback to MOCK_LOCATION_DB if JSON file is missing or incomplete
        locations_by_state: Dict[str, Dict[str, Any]] = {}
        for s_name, districts in MOCK_LOCATION_DB.items():
            dist_list = []
            for d_name, complexes in districts.items():
                dist_list.append({
                    "dist_code": d_name,
                    "dist_name": d_name,
                    "complexes": [{"complex_code": c, "complex_name": c} for c in complexes]
                })
            norm_k = normalize_text(s_name)
            locations_by_state[norm_k] = {
                "state_code": s_name,
                "state_name": s_name,
                "districts": dist_list
            }

        sorted_states = sorted(locations_by_state.values(), key=lambda s: s["state_name"])
        self._cached_data = {"states": sorted_states}
        return self._cached_data

    def get_all(self) -> Dict[str, Any]:
        """Return the complete state-district-complex tree."""
        return self.load_data()

    def get_states(self) -> List[Dict[str, str]]:
        """Return sorted list of available states."""
        all_data = self.get_all()
        return [
            {"state_code": s["state_code"], "state_name": s["state_name"], "code": s["state_code"], "name": s["state_name"]}
            for s in all_data["states"]
        ]

    def get_districts(self, state_query: str) -> List[Dict[str, Any]]:
        """Return districts for a given state (by name or code)."""
        all_data = self.get_all()
        norm_q = normalize_text(state_query)
        canon_q = canonical_key(state_query)
        for s in all_data["states"]:
            if (
                s["state_code"] == state_query
                or normalize_text(s["state_name"]) == norm_q
                or canonical_key(s["state_name"]) == canon_q
                or norm_q in normalize_text(s["state_name"])
            ):
                return sorted(
                    [
                        {
                            "dist_code": d["dist_code"],
                            "dist_name": d["dist_name"],
                            "code": d["dist_code"],
                            "name": d["dist_name"],
                            "complex_count": len(d.get("complexes", []))
                        }
                        for d in s.get("districts", [])
                    ],
                    key=lambda d: d["dist_name"]
                )
        return []

    def get_court_complexes(self, state_query: str, district_query: str) -> List[Dict[str, str]]:
        """Return court complexes for a given state and district."""
        all_data = self.get_all()
        norm_s = normalize_text(state_query)
        canon_s = canonical_key(state_query)
        norm_d = normalize_text(district_query)
        canon_d = canonical_key(district_query)

        for s in all_data["states"]:
            if (
                s["state_code"] == state_query
                or normalize_text(s["state_name"]) == norm_s
                or canonical_key(s["state_name"]) == canon_s
                or norm_s in normalize_text(s["state_name"])
            ):
                for d in s.get("districts", []):
                    if (
                        d["dist_code"] == district_query
                        or normalize_text(d["dist_name"]) == norm_d
                        or canonical_key(d["dist_name"]) == canon_d
                        or norm_d in normalize_text(d["dist_name"])
                    ):
                        return sorted(
                            [
                                {
                                    "complex_code": c["complex_code"],
                                    "complex_name": c["complex_name"],
                                    "code": c["complex_code"],
                                    "name": c["complex_name"]
                                }
                                for c in d.get("complexes", [])
                            ],
                            key=lambda c: c["complex_name"]
                        )
        return []

    # Alias for backward compatibility
    def get_complexes(self, state_code: str, dist_code: str) -> List[Dict[str, str]]:
        return self.get_court_complexes(state_code, dist_code)


location_service = LocationService()
