"""Pipeline orchestration API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.models.pipeline import PipelineExecutionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipelines", tags=["pipelines"])


# Response models
class PipelineListResponse(BaseModel):
    """Response model for listing pipelines."""
    pipelines: list[str]
    count: int


class PipelineDetailResponse(BaseModel):
    """Response model for pipeline details."""
    name: str
    description: str
    version: str
    enabled: bool
    steps: list[dict[str, Any]]
    tags: list[str]


class PipelineExecutionRequest(BaseModel):
    """Request model for pipeline execution."""
    inputs: dict[str, Any] | None = None


# Dependency injection
def get_pipeline_registry(request: Request) -> PipelineRegistry:
    """Get pipeline registry from app state."""
    return request.app.state.pipeline_registry


def get_orchestrator(request: Request) -> PipelineOrchestrator:
    """Get pipeline orchestrator from app state."""
    return request.app.state.pipeline_orchestrator


@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    registry: PipelineRegistry = Depends(get_pipeline_registry)
) -> PipelineListResponse:
    """
    List all available pipelines.

    Returns:
        List of pipeline names and count
    """
    pipelines = registry.list_pipelines()

    return PipelineListResponse(
        pipelines=pipelines,
        count=len(pipelines)
    )


@router.get("/{pipeline_name}", response_model=PipelineDetailResponse)
async def get_pipeline(
    pipeline_name: str,
    registry: PipelineRegistry = Depends(get_pipeline_registry)
) -> PipelineDetailResponse:
    """
    Get pipeline configuration details.

    Args:
        pipeline_name: Name of pipeline to retrieve

    Returns:
        Pipeline configuration details

    Raises:
        HTTPException: 404 if pipeline not found
    """
    try:
        config = registry.get_pipeline(pipeline_name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline '{pipeline_name}' not found"
        )

    # Convert to response model
    return PipelineDetailResponse(
        name=config.name,
        description=config.description,
        version=config.version,
        enabled=config.enabled,
        steps=[
            {
                "name": step.name,
                "type": step.type.value,
                "connector": step.connector,
                "on_error": step.on_error.value
            }
            for step in config.steps
        ],
        tags=config.tags
    )


@router.post("/{pipeline_name}/run", response_model=PipelineExecutionResult)
async def execute_pipeline(
    pipeline_name: str,
    request_body: PipelineExecutionRequest = PipelineExecutionRequest(),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator)
) -> PipelineExecutionResult:
    """
    Execute a pipeline.

    Args:
        pipeline_name: Name of pipeline to execute
        request_body: Optional inputs for pipeline execution

    Returns:
        Pipeline execution result

    Raises:
        HTTPException: 404 if pipeline not found
        HTTPException: 400 if pipeline execution fails
    """
    logger.info(f"Executing pipeline: {pipeline_name}")

    try:
        result = await orchestrator.execute_pipeline(
            pipeline_name=pipeline_name,
            inputs=request_body.inputs
        )

        return result

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline '{pipeline_name}' not found"
        )
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@router.post("/{pipeline_name}/reload")
async def reload_pipeline(
    pipeline_name: str,
    registry: PipelineRegistry = Depends(get_pipeline_registry)
) -> dict[str, str]:
    """
    Reload pipeline configuration from disk.

    Args:
        pipeline_name: Name of pipeline to reload

    Returns:
        Success message

    Raises:
        HTTPException: 404 if pipeline not found after reload
    """
    logger.info(f"Reloading pipeline: {pipeline_name}")

    registry.reload()

    try:
        registry.get_pipeline(pipeline_name)
        return {"status": "success", "message": f"Pipeline '{pipeline_name}' reloaded"}
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline '{pipeline_name}' not found after reload"
        )
