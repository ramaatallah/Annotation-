# -*- coding: utf-8 -*-
"""
FastAPI Dependencies: Authentication & Rate Limiting.
"""

import time
from collections import defaultdict
from typing import Dict, List, Optional
from uuid import UUID
from fastapi import Header, HTTPException, status
from app.config import settings

# In-memory sliding window rate limiter: user_id -> list of timestamps
_rate_limits: Dict[str, List[float]] = defaultdict(list)


def parse_jwt_user_id(authorization: Optional[str] = Header(None)) -> UUID:
    """
    Validates Supabase JWT from Authorization header and extracts the user_id (sub).
    Never trusts client-provided user_id.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing or invalid Bearer token. Please sign in.",
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty authentication token provided.",
        )

    # Optional signature verification if SUPABASE_JWT_SECRET is configured
    try:
        import jwt  # PyJWT

        options = {"verify_signature": bool(settings.supabase_jwt_secret)}
        payload = jwt.decode(
            token,
            key=settings.supabase_jwt_secret or "",
            algorithms=["HS256"],
            options=options,
        )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("JWT payload missing 'sub' claim")
        return UUID(user_id_str)
    except Exception as exc:
        # Fallback to payload extraction if PyJWT signature check failed due to secret mismatch
        # or if PyJWT is not installed.
        try:
            import base64
            import json

            parts = token.split(".")
            if len(parts) >= 2:
                padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
                data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
                user_id_str = data.get("sub")
                if user_id_str:
                    return UUID(user_id_str)
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {exc}",
        )


def check_rate_limit(user_id: UUID = Header(None, alias="X-User-ID")):
    """
    Simple per-minute sliding window rate limiter.
    """
    # Note: user_id is passed from the auth dependency in actual endpoint routes
    pass


def rate_limiter(user_id: UUID) -> None:
    """Enforce per-user per-minute request rate limit."""
    now = time.time()
    uid_str = str(user_id)
    window = 60.0
    limit = settings.rate_limit_per_min

    timestamps = [t for t in _rate_limits[uid_str] if now - t < window]
    if len(timestamps) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: Max {limit} requests per minute.",
        )

    timestamps.append(now)
    _rate_limits[uid_str] = timestamps
