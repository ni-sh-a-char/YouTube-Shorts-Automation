"""
scripts/runner.py

Tiny runner wrapper that exposes `generate_and_upload_short()` which
calls into the scheduler's generation routine. This provides a stable
import location for external callers (as requested).
"""
from typing import Dict

try:
    from scheduler import generate_and_upload_short as _generate
except Exception:
    # Fallback in case scheduler isn't importable at module import time
    def _generate() -> Dict:
        from scheduler import generate_shorts_video
        return generate_shorts_video()


def generate_and_upload_short() -> Dict:
    """Run the shorts generation task and return result dict."""
    return _generate()
