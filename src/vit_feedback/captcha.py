import re
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_ocr_instance = None

def get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        try:
            import ddddocr
            _ocr_instance = ddddocr.DdddOcr(show_ad=False)
        except Exception as e:
            logger.error("Failed to initialize ddddocr: %s", e)
            raise RuntimeError(f"ddddocr initialization failed: {e}") from e
    return _ocr_instance

def clean_captcha_text(text: str) -> str:
    """Strip spaces and non-alphanumeric noise."""
    if not text:
        return ""
    # Keep only ASCII alphanumeric characters
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", text.strip())
    return cleaned

def solve_captcha_bytes(image_bytes: bytes) -> str:
    """Classify captcha image bytes using ddddocr."""
    if not image_bytes:
        return ""
    ocr = get_ocr()
    raw_res = ocr.classification(image_bytes)
    return clean_captcha_text(raw_res)

def solve_captcha_base64(data_uri: str) -> str:
    """Extract and solve captcha from data URI (e.g. data:image/jpeg;base64,...)."""
    if not data_uri or not isinstance(data_uri, str) or "," not in data_uri:
        raise ValueError(f"Invalid data URI: {data_uri[:50] if data_uri else None}")
    
    parts = data_uri.split(",", 1)
    if len(parts) != 2:
        raise ValueError("Invalid base64 data URI format")
    
    b64_str = parts[1].strip()
    image_bytes = base64.b64decode(b64_str)
    return solve_captcha_bytes(image_bytes)
