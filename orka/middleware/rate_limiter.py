# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Rate Limiter Middleware
=======================

Rate limiting middleware for OrKa REST API to prevent abuse in public deployments.
Uses slowapi for Redis-backed or in-memory rate limiting.

Features:
- Per-IP rate limiting
- Configurable limits via environment variables
- 429 Too Many Requests responses
- Integration with FastAPI
"""

import logging
import os
from typing import Callable

from fastapi import Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler  # type: ignore
from slowapi.errors import RateLimitExceeded  # type: ignore
from slowapi.util import get_remote_address  # type: ignore

logger = logging.getLogger(__name__)


def get_rate_limit() -> str:
    """
    Get rate limit from environment variable.

    Returns:
        str: Rate limit string in format "N/unit" (e.g., "5/minute")
    """
    limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "5"))
    return f"{limit_per_minute}/minute"


def get_client_identifier(request: Request) -> str:
    """
    Get client identifier for rate limiting.

    Tries to get real IP from headers (Cloud Run forwarding),
    falls back to remote address.

    Args:
        request: FastAPI request object

    Returns:
        str: Client IP address
    """
    # Cloud Run and load balancers set X-Forwarded-For header
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP in the chain (client IP)
        client_ip = forwarded_for.split(",")[0].strip()
        return str(client_ip)

    # Fallback to direct connection IP
    return str(get_remote_address(request))


# Initialize limiter with custom key function
limiter = Limiter(
    key_func=get_client_identifier,
    default_limits=[get_rate_limit()],
    storage_uri="memory://",  # In-memory storage (sufficient for single instance)
    # For multi-instance deployments, use Redis:
    # storage_uri=os.getenv("REDIS_URL", "redis://localhost:6380/1")
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception

    Returns:
        Response: 429 JSON response with retry information
    """
    client_ip = get_client_identifier(request)
    logger.warning(
        f"Rate limit exceeded for client {client_ip}: {exc.detail}",
    )

    return Response(
        content=f'{{"error": "Rate limit exceeded", "detail": "{exc.detail}", "client_ip": "{client_ip}"}}',
        status_code=429,
        headers={"Content-Type": "application/json"},
    )


# Export limiter for use in server.py
__all__ = ["limiter", "rate_limit_exceeded_handler", "get_rate_limit"]
