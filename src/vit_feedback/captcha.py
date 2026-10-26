import io
import re
import base64
import logging
from typing import Optional
from PIL import Image
import numpy as np

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
    return re.sub(r"[^a-zA-Z0-9]", "", text.strip())

def preprocess_captcha_image(image_bytes: bytes) -> bytes:
    """Isolate blue text pixels and remove background grid lines and noise."""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        # In VIT captchas, letters are saturated blue: Blue > 110, Red < 120, Green < 120
        blue_mask = (arr[:, :, 2] > 110) & (arr[:, :, 0] < 120) & (arr[:, :, 1] < 120)
        # Create crisp binary image: 0 for text (black), 255 for background (white)
        clean = np.ones((arr.shape[0], arr.shape[1]), dtype=np.uint8) * 255
        clean[blue_mask] = 0
        
        buf = io.BytesIO()
        Image.fromarray(clean).save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        logger.debug("Preprocessing failed, falling back to raw bytes: %s", e)
        return image_bytes

def solve_captcha_bytes(image_bytes: bytes) -> str:
    """Classify captcha image bytes using color thresholding and ddddocr."""
    if not image_bytes:
        return ""
    ocr = get_ocr()
    
    # Try preprocessed image first
    cleaned_bytes = preprocess_captcha_image(image_bytes)
    pred = clean_captcha_text(ocr.classification(cleaned_bytes))
    if len(pred) == 6:
        return pred

    # Fallback to raw image if cleaned didn't yield 6 chars
    raw_pred = clean_captcha_text(ocr.classification(image_bytes))
    return raw_pred if len(raw_pred) == 6 else (pred or raw_pred)

def solve_captcha_base64(data_uri: str) -> str:
    """Extract and solve captcha from data URI."""
    if not data_uri or not isinstance(data_uri, str) or "," not in data_uri:
        raise ValueError(f"Invalid data URI: {data_uri[:50] if data_uri else None}")
    
    parts = data_uri.split(",", 1)
    if len(parts) != 2:
        raise ValueError("Invalid base64 data URI format")
    
    b64_str = parts[1].strip()
    image_bytes = base64.b64decode(b64_str)
    return solve_captcha_bytes(image_bytes)
