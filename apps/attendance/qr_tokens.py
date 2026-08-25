"""Time-sensitive HMAC tokens powering the Teacher Attendance QR system.

The dashboard displays a QR code whose payload is::

    TEACHER_ATT|YYYY-MM-DD|<32-char HMAC-SHA256 signature>

The signature is derived from ``settings.SECRET_KEY`` and the date, so the
token is stateless yet impossible to forge without the server secret. Tokens
are only accepted when their embedded date equals *today*, which makes every
previous day's code instantly useless (a fresh code is generated each day).
"""

import hashlib
import hmac

from django.conf import settings

PREFIX = "TEACHER_ATT"
SEPARATOR = "|"


def _signature(payload_date: str) -> str:
    message = f"teacher-attendance:{payload_date}".encode()
    digest = hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256)
    return digest.hexdigest()[:32]


def generate_token(for_date) -> str:
    """Build the QR payload for the given calendar date."""
    date_str = for_date.strftime("%Y-%m-%d")
    return f"{PREFIX}{SEPARATOR}{date_str}{SEPARATOR}{_signature(date_str)}"


def verify_token(token, today) -> tuple[bool, str]:
    """Validate a scanned token against *today*.

    Returns ``(is_valid, reason)``. Reasons are user-friendly strings safe to
    surface in the mobile app dialog.
    """
    if not token or not isinstance(token, str):
        return False, "Empty QR payload."
    parts = token.strip().split(SEPARATOR)
    if len(parts) != 3 or parts[0] != PREFIX:
        return False, "Unrecognised QR payload."
    _, token_date, signature = parts
    if not hmac.compare_digest(signature, _signature(token_date)):
        return False, "Invalid or tampered QR code."
    if token_date != today.strftime("%Y-%m-%d"):
        return False, "This QR code has expired. Scan today's code from the dashboard."
    return True, ""