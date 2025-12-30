"""Connector metadata API endpoints."""

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from flexlink.core.registry import ConnectorRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/connectors", tags=["connectors"])


class ConnectorInfo(BaseModel):
    """Connector metadata."""
    name: str
    type: str
    description: str | None = None


class ConnectorListResponse(BaseModel):
    """Response for connector listing."""
    connectors: list[ConnectorInfo]
    count: int


def get_connector_registry(request: Request) -> ConnectorRegistry:
    """Get connector registry from dependencies."""
    from flexlink.api.dependencies import get_registry
    return get_registry()


@router.get("", response_model=ConnectorListResponse)
async def list_connectors(
    registry: ConnectorRegistry = Depends(get_connector_registry)
) -> ConnectorListResponse:
    """
    List all available connectors.

    Returns connector names and types for UI reference and validation.

    Returns:
        List of connectors with metadata
    """
    connector_names = registry.list_connectors()

    connectors = []
    for name in connector_names:
        connector = registry.get_connector(name)

        # Determine connector type from class name
        connector_type = type(connector).__name__.replace("Connector", "").lower()

        connectors.append(ConnectorInfo(
            name=name,
            type=connector_type,
            description=f"{connector_type.title()} connector"
        ))

    return ConnectorListResponse(
        connectors=connectors,
        count=len(connectors)
    )
