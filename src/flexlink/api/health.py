"""Health check endpoints."""

import platform
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, status

from flexlink.api.dependencies import get_registry
from flexlink.core.registry import ConnectorRegistry

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """
    Basic health check endpoint.

    Returns:
        Health status with timestamp
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check(
    registry: ConnectorRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """
    Detailed health check with system information.

    Args:
        registry: ConnectorRegistry dependency

    Returns:
        Detailed health status including system info and components
    """
    connectors = registry.list_connectors()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
        },
        "components": {
            "api": "healthy",
            "file_processing": "healthy",
            "connectors": {"count": len(connectors), "names": connectors},
        },
    }
