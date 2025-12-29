"""Mapping metadata API endpoints."""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from flexlink.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mappings", tags=["mappings"])


class MappingInfo(BaseModel):
    """Mapping metadata."""
    name: str
    path: str


class MappingListResponse(BaseModel):
    """Response for mapping listing."""
    mappings: list[MappingInfo]
    count: int


@router.get("", response_model=MappingListResponse)
async def list_mappings() -> MappingListResponse:
    """
    List all available mapping configurations.

    Scans the config/mappings directory for YAML files.

    Returns:
        List of mapping names and file paths
    """
    settings = get_settings()
    mappings_dir = settings.config_dir / "mappings"

    if not mappings_dir.exists():
        return MappingListResponse(mappings=[], count=0)

    mappings = []
    for yaml_file in mappings_dir.glob("*.yaml"):
        mapping_name = yaml_file.stem
        mappings.append(MappingInfo(
            name=mapping_name,
            path=str(yaml_file.relative_to(settings.config_dir))
        ))

    return MappingListResponse(
        mappings=sorted(mappings, key=lambda m: m.name),
        count=len(mappings)
    )
