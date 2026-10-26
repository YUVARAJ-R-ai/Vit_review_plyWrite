import base64
import pytest
from vit_feedback.captcha import solve_captcha_bytes, solve_captcha_base64

# Sample dummy 1x1 png base64
DUMMY_PNG_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

def test_solve_captcha_base64_invalid():
    with pytest.raises(ValueError):
        solve_captcha_base64("not_a_valid_data_uri")

def test_solve_captcha_from_file_if_exists(tmp_path):
    # Test that solve_captcha_bytes runs and returns a string
    dummy_bytes = base64.b64decode(DUMMY_PNG_B64.split(",")[1])
    result = solve_captcha_bytes(dummy_bytes)
    assert isinstance(result, str)

def test_solve_captcha_real_sample():
    # If /tmp/fresh_captcha2.jpg exists, verify prediction has length > 0
    import os
    if os.path.exists("/tmp/fresh_captcha2.jpg"):
        with open("/tmp/fresh_captcha2.jpg", "rb") as f:
            data = f.read()
        res = solve_captcha_bytes(data)
        assert len(res) == 6
