"""
Automated CAPTCHA Solver Service using ddddocr.
Provides local, fast, and completely offline recognition for eCourts Securimage captchas.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("ecourts_search.captcha_solver")


class CaptchaSolver:
    """
    Singleton service wrapper around ddddocr for CAPTCHA recognition.
    """
    def __init__(self):
        self._ocr = None

    def _get_ocr(self):
        if self._ocr is None:
            import ddddocr
            logger.info("Initializing ddddocr engine for automated CAPTCHA recognition...")
            self._ocr = ddddocr.DdddOcr(show_ad=False)
        return self._ocr

    def solve(self, image_bytes: bytes) -> Optional[str]:
        """
        Takes raw image bytes from Playwright screenshot or HTTP response,
        runs OCR, and returns a clean lowercase alphanumeric string.
        """
        if not image_bytes:
            logger.warning("Empty image bytes received for CAPTCHA solving.")
            return None

        try:
            ocr = self._get_ocr()
            raw_text = ocr.classification(image_bytes)
            if not raw_text:
                logger.warning("ddddocr returned empty prediction.")
                return None

            # eCourts Securimage CAPTCHAs are alphanumeric (lowercase/digits, usually 6 chars)
            cleaned = re.sub(r"[^a-zA-Z0-9]", "", raw_text.strip().lower())
            logger.info("CAPTCHA solved automatically: '%s'", cleaned)
            return cleaned
        except Exception as exc:
            logger.error("Failed to solve CAPTCHA via ddddocr: %s", exc, exc_info=True)
            return None


captcha_solver = CaptchaSolver()
