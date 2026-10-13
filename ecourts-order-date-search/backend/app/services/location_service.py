"""
Location service providing cascading Indian States, Districts, and Court Complexes.
Loads from persistent cache for instant (0ms) response and falls back to
live eCourts retrieval for uncached selections, caching them for future requests.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "locations_cache.json")


class LocationService:
    def __init__(self):
        self._cache: Dict[str, Any] = {
            "states": [],
            "districts": {},
            "complexes": {}
        }
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache.get('states', []))} states from locations cache.")
            except Exception as e:
                logger.error(f"Failed to load locations cache: {e}")

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write locations cache: {e}")

    def get_states(self) -> List[Dict[str, str]]:
        """Return list of all Indian States and Union Territories with official eCourts codes."""
        states = self._cache.get("states", [])
        return sorted(states, key=lambda s: s.get("name", ""))

    async def get_districts(self, state_code: str) -> List[Dict[str, str]]:
        """Return districts for a given state code. Fetches live if not in cache."""
        districts_map = self._cache.setdefault("districts", {})
        if state_code in districts_map and districts_map[state_code]:
            return districts_map[state_code]

        # Fetch live from eCourts
        logger.info(f"Districts for state {state_code} not cached. Fetching live from eCourts...")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
                )
                await page.goto("https://services.ecourts.gov.in/ecourtindia_v6/?p=courtorder%2Findex", wait_until="domcontentloaded", timeout=30000)
                await page.select_option("select#sess_state_code", state_code)
                await page.wait_for_function("() => document.querySelector('select#sess_dist_code').options.length > 1", timeout=12000)

                districts = await page.evaluate("""() => {
                    const sel = document.querySelector('select#sess_dist_code');
                    if (!sel) return [];
                    return Array.from(sel.options)
                        .filter(o => o.value && o.value !== '0' && o.text.trim())
                        .map(o => ({ code: o.value, name: o.text.trim() }));
                }""")
                await browser.close()

                if districts:
                    districts_map[state_code] = districts
                    self._save_cache()
                    logger.info(f"Cached {len(districts)} districts for state {state_code}.")
                    return districts
        except Exception as e:
            logger.warning(f"Live district fetch failed for state {state_code}: {e}")

        return []

    async def get_complexes(self, state_code: str, dist_code: str) -> List[Dict[str, str]]:
        """Return court complexes for a given state & district. Fetches live if not in cache."""
        complexes_map = self._cache.setdefault("complexes", {})
        cache_key = f"{state_code}_{dist_code}"

        if cache_key in complexes_map and complexes_map[cache_key]:
            return complexes_map[cache_key]

        # Fetch live from eCourts
        logger.info(f"Complexes for {cache_key} not cached. Fetching live from eCourts...")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
                )
                await page.goto("https://services.ecourts.gov.in/ecourtindia_v6/?p=courtorder%2Findex", wait_until="domcontentloaded", timeout=30000)
                await page.select_option("select#sess_state_code", state_code)
                await page.wait_for_function("() => document.querySelector('select#sess_dist_code').options.length > 1", timeout=12000)

                await page.select_option("select#sess_dist_code", dist_code)
                await page.wait_for_function("() => document.querySelector('select#court_complex_code').options.length > 1", timeout=12000)

                complexes = await page.evaluate("""() => {
                    const sel = document.querySelector('select#court_complex_code');
                    if (!sel) return [];
                    return Array.from(sel.options)
                        .filter(o => o.value && o.value !== '0' && o.text.trim())
                        .map(o => ({ code: o.value, name: o.text.trim() }));
                }""")
                await browser.close()

                if complexes:
                    complexes_map[cache_key] = complexes
                    self._save_cache()
                    logger.info(f"Cached {len(complexes)} complexes for {cache_key}.")
                    return complexes
        except Exception as e:
            logger.warning(f"Live complex fetch failed for {cache_key}: {e}")

        return []


# Singleton instance
location_service = LocationService()
