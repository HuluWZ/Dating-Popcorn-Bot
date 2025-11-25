"""
Helpers for working with user-supplied media files.
"""

from __future__ import annotations

from typing import Optional


def validate_image_content(file_content: bytes) -> Optional[str]:
    """
    Validate the image bytes by checking magic numbers.

    Returns the detected extension or None when invalid.
    """
    if not file_content or len(file_content) < 4:
        return None

    if file_content[:3] == b"\xff\xd8\xff":
        return "jpg"

    if file_content[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"

    if file_content[:4] == b"GIF8":
        return "gif"

    if file_content[:2] == b"BM":
        return "bmp"

    if file_content[:4] == b"RIFF" and file_content[8:12] == b"WEBP":
        return "webp"

    if file_content[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"

    return None

