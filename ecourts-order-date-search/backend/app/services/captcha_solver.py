"""
Automated CAPTCHA Solver Service using ddddocr.
Provides local, fast, and completely offline recognition for eCourts Securimage captchas.
"""

import io
import re
import logging
from typing import Optional
from PIL import Image

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

    def preprocess_image(self, image_bytes: bytes) -> bytes:
        """
        Normalize image: ensure RGB format on clean white background
        to eliminate alpha transparency artifacts that degrade OCR accuracy.
        """
        try:
            im = Image.open(io.BytesIO(image_bytes))
            if im.mode in ("RGBA", "LA", "P"):
                if im.mode == "P":
                    im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                if "A" in im.getbands():
                    bg.paste(im, mask=im.split()[-1])
                else:
                    bg.paste(im, (0, 0))
                buf = io.BytesIO()
                bg.save(buf, format="PNG")
                return buf.getvalue()
            elif im.mode != "RGB":
                im = im.convert("RGB")
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                return buf.getvalue()
        except Exception as e:
            logger.debug("Image preprocessing bypassed: %s", e)
        return image_bytes

    def solve(self, image_bytes: bytes) -> Optional[str]:
        """
        Takes raw image bytes from Playwright screenshot or canvas extraction,
        runs OCR, and returns a clean lowercase alphanumeric string.
        """
        if not image_bytes:
            logger.warning("Empty image bytes received for CAPTCHA solving.")
            return None

        if len(image_bytes) < 300:
            logger.warning("CAPTCHA image bytes suspiciously small (%d bytes) - element unrendered or blank.", len(image_bytes))
            return None

        try:
            processed_bytes = self.preprocess_image(image_bytes)
            ocr = self._get_ocr()
            raw_text = ocr.classification(processed_bytes)
            if not raw_text:
                logger.warning("ddddocr returned empty prediction on %d bytes.", len(processed_bytes))
                return None

            # eCourts Securimage CAPTCHAs are alphanumeric (lowercase/digits, usually 5-6 chars)
            cleaned = re.sub(r"[^a-zA-Z0-9]", "", raw_text.strip().lower())
            if not cleaned:
                logger.warning("ddddocr output '%s' contained no alphanumeric characters.", raw_text)
                return None

            logger.info("CAPTCHA solved automatically: '%s' (from raw OCR: '%s')", cleaned, raw_text)
            return cleaned
        except Exception as exc:
            logger.error("Failed to solve CAPTCHA via ddddocr: %s", exc, exc_info=True)
            return None


captcha_solver = CaptchaSolver()
