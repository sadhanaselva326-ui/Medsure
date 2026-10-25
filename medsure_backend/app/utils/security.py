import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class RateLimiter:
    """Sliding-window in-memory rate limiter per IP address."""

    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.records: Dict[str, List[float]] = defaultdict(list)

    def check(self, ip: str) -> bool:
        now = time.time()
        window_start = now - 60.0
        # Discard requests outside current 60s window
        valid_requests = [t for t in self.records[ip] if t > window_start]
        self.records[ip] = valid_requests

        if len(valid_requests) >= self.requests_per_minute:
            return False

        self.records[ip].append(now)
        return True


rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)


async def verify_admin_key(api_key: Optional[str] = Security(api_key_header)) -> bool:
    """Verify X-API-Key header for admin-only endpoints.

    Key resolution order:
      1. ADMIN_API_KEY  (dedicated admin key, preferred)
      2. SECRET_KEY     (general secret key, fallback)

    Behaviour:
      - DEBUG=True  → always allowed (no key required)
      - Neither key configured in production → 503 (misconfiguration, not 403)
      - Key present but wrong → 403
    """
    if settings.DEBUG:
        return True

    # Determine which key(s) are authoritative
    valid_keys = [k for k in [settings.ADMIN_API_KEY, settings.SECRET_KEY] if k]

    if not valid_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Admin API key is not configured on this server. "
                "Set ADMIN_API_KEY or SECRET_KEY in the environment."
            ),
        )

    if api_key and api_key in valid_keys:
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid or missing API key for administrative operations.",
    )
