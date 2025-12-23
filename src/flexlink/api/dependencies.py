"""Dependency injection for FastAPI routes."""


from fastapi import HTTPException, status

from flexlink.core.registry import ConnectorRegistry
from flexlink.core.router import RequestRouter

# Global instances (set by main.py during startup)
_registry: ConnectorRegistry | None = None
_router: RequestRouter | None = None


def set_registry(registry: ConnectorRegistry) -> None:
    """
    Set global registry instance.

    Called during application startup.

    Args:
        registry: ConnectorRegistry instance
    """
    global _registry
    _registry = registry


def set_router(router: RequestRouter) -> None:
    """
    Set global router instance.

    Called during application startup.

    Args:
        router: RequestRouter instance
    """
    global _router
    _router = router


def get_registry() -> ConnectorRegistry:
    """
    Get ConnectorRegistry instance for dependency injection.

    Returns:
        ConnectorRegistry instance

    Raises:
        HTTPException: If registry not initialized
    """
    if _registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ConnectorRegistry not initialized",
        )
    return _registry


def get_router() -> RequestRouter:
    """
    Get RequestRouter instance for dependency injection.

    Returns:
        RequestRouter instance

    Raises:
        HTTPException: If router not initialized
    """
    if _router is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RequestRouter not initialized",
        )
    return _router
