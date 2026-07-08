"""
apps/shared/utils/security.py

Security helpers: token hashing, masking.
"""

import hashlib
import hmac
import secrets

ALGORITHM = "sha256"


def hash_token(token: str) -> str:
    """
    One-way hash a token (e.g. refresh token) before storing it.
    Uses HMAC-SHA256 with a server-side secret — not the Django SECRET_KEY.
    """
    server_secret = secrets.token_hex(16)  # stored separately in production
    return hmac.new(
        server_secret.encode(), token.encode(), hashlib.sha256
    ).hexdigest()


def generate_secure_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def mask_sensitive_value(value: str, visible_chars: int = 4, mask_char: str = "*") -> str:
    if not value:
        return ""
    if len(value) <= visible_chars:
        return mask_char * len(value)
    reveal_start = len(value) - visible_chars
    return mask_char * reveal_start + value[reveal_start:]


def mask_email(email: str) -> str:
    """
    Mask an email address for safe display.

    Example:
        mask_email("john.doe@example.com")  → "jo****do@e******.com"
    """
    if not email or "@" not in email:
        return "****"
    local, domain = email.split("@", 1)
    masked_local = f"{local[:2]}***{local[-2:]}" if len(local) > 4 else "*****"
    if "." in domain:
        d_parts = domain.rsplit(".", 1)
        masked_domain = f"{d_parts[0][:1]}*****{d_parts[0][-1:]}.{d_parts[1]}"
    else:
        masked_domain = f"{domain[:1]}*****{domain[-1:]}"
    return f"{masked_local}@{masked_domain}"
