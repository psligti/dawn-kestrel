"""Health check endpoint module for WebApp API."""

from fastapi import APIRouter
from typing import Dict

from .constants import APP_VERSION


router = APIRouter()


@router.get("/health", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """Health check endpoint.

    Returns the current status of the API and version information.
    This endpoint can be extended to check database connectivity,
    external service availability, etc.

    Returns:
        Dict[str, str]: API status and version information
    """
    return {
        "status": "ok",
        "version": APP_VERSION,
    }
