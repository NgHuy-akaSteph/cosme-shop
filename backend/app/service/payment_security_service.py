"""Xac thuc chu ky webhook (HMAC-SHA256) - chong gia mao + chong replay"""

import hashlib
import hmac
import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

# SePay chap nhan request trong toi da 300 giay
MAX_TIMESTAMP_SKEW_SECONDS = 300

API_KEY_PREFIX = "Apikey "


def verify_webhook_signature(
    raw_body: bytes,
    signature: str | None,
    timestamp: str | None,
    secret: str | None,
) -> tuple[bool, str]:
    """
    Kiem tra chu ky HMAC-SHA256 cua SePay.

    SePay ky: `sha256={hex}` tren chuoi `{timestamp}.{raw_body}`,
    gui kem header `X-SePay-Signature` va `X-SePay-Timestamp`.

    Returns:
        (ok, error_code) - error_code: "missing_secret" | "missing_headers"
                           | "expired" | "invalid_signature" | ""
    """
    if not secret:
        return False, "missing_secret"

    if not signature or not timestamp:
        return False, "missing_headers"

    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False, "missing_headers"

    # Chong replay: request cu hon 5 phut -> reject
    if abs(time.time() - ts) > MAX_TIMESTAMP_SKEW_SECONDS:
        logger.warning(
            "Webhook: timestamp %s lech qua %ss", ts, MAX_TIMESTAMP_SKEW_SECONDS
        )
        return False, "expired"

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        f"{ts}.".encode("utf-8") + raw_body,
        hashlib.sha256,
    ).hexdigest()

    # constant-time compare
    if not hmac.compare_digest(expected.encode("utf-8"), signature.encode("utf-8")):
        logger.warning("Webhook: chu ky khong khop")
        return False, "invalid_signature"

    return True, ""


def verify_api_key(authorization: str | None, expected_key: str | None) -> tuple[bool, str]:
    """
    Kiem tra API key dang header `Authorization: Apikey <key>`.

    Returns:
        (ok, error_code) - error_code: "invalid_api_key" | ""
    """
    if not expected_key:
        return False, "invalid_api_key"

    provided = (
        authorization[len(API_KEY_PREFIX):]
        if authorization and authorization.startswith(API_KEY_PREFIX)
        else ""
    )
    if not hmac.compare_digest(provided.encode(), expected_key.encode()):
        return False, "invalid_api_key"

    return True, ""


def authenticate_webhook_request(
    raw_body: bytes,
    authorization: str | None,
    signature: str | None,
    timestamp: str | None,
) -> tuple[bool, str]:
    """
    Xac thuc webhook theo thu tu uu tien:
    1. Neu co SEPAY_WEBHOOK_SECRET -> bat buoc HMAC-SHA256 (khuyen nghi).
    2. Neu khong co secret -> fallback API Key (de tam thu muc do).
    """
    if settings.SEPAY_WEBHOOK_SECRET:
        return verify_webhook_signature(
            raw_body, signature, timestamp, settings.SEPAY_WEBHOOK_SECRET
        )

    return verify_api_key(authorization, settings.SEPAY_API_KEY)
