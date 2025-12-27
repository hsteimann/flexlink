"""FlexLink Middleware FastAPI Application."""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from flexlink.api import dependencies, files, health, pipelines, routes
from flexlink.config import get_settings, load_route_configs
from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.router import RequestRouter
from flexlink.core.scheduler_service import SchedulerService
from flexlink.core.transformation import TransformationEngine
from flexlink.middleware.error_handling import ErrorHandlingMiddleware
from flexlink.middleware.logging import LoggingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Global instances
http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """
    Application lifespan: startup and shutdown.

    Handles:
    - HTTP client initialization
    - Connector registry loading
    - Request router initialization
    - Route configuration loading
    - Cleanup on shutdown
    """
    global http_client

    # Startup
    logger.info("Starting FlexLink Middleware...")
    settings = get_settings()

    # Create HTTP client for REST connectors
    http_client = httpx.AsyncClient()
    logger.info("HTTP client initialized")

    # Initialize connector registry
    registry = ConnectorRegistry()

    # Create config directory if it doesn't exist
    settings.config_dir.mkdir(parents=True, exist_ok=True)

    try:
        await registry.load_connectors(
            http_client=http_client, config_dir=settings.config_dir
        )
        logger.info(f"Loaded connectors: {registry.list_connectors()}")
    except Exception as e:
        logger.warning(f"No connectors loaded: {e}")
        logger.info("Starting without connectors (use /api/v1/connectors to check)")

    # Initialize request router
    router = RequestRouter(registry, config_dir=settings.config_dir)
    logger.info("Request router initialized")

    # Load route configurations from YAML files
    try:
        route_configs = load_route_configs(settings.config_dir)
        router.add_routes(route_configs)
        logger.info(f"Loaded {len(route_configs)} route configurations")
    except Exception as e:
        logger.warning(f"No routes loaded: {e}")
        logger.info("Starting without routes (routes can be added via API)")

    # Set global dependencies
    dependencies.set_registry(registry)
    dependencies.set_router(router)
    logger.info("Dependencies initialized")

    # Initialize pipeline registry
    logger.info("Loading pipeline configurations")
    pipeline_registry = PipelineRegistry()
    try:
        pipeline_registry.load_pipelines()
        logger.info(f"Loaded {len(pipeline_registry.list_pipelines())} pipelines")
    except Exception as e:
        logger.warning(f"No pipelines loaded: {e}")
        logger.info("Starting without pipelines (pipelines can be added via config)")

    # Initialize pipeline orchestrator
    logger.info("Initializing pipeline orchestrator")
    transformation_engine = TransformationEngine(rules=[])
    orchestrator = PipelineOrchestrator(
        pipeline_registry=pipeline_registry,
        connector_registry=registry,
        transformation_engine=transformation_engine
    )

    # Store in app state for dependency injection
    app.state.pipeline_registry = pipeline_registry
    app.state.pipeline_orchestrator = orchestrator
    logger.info("Pipeline orchestrator initialized")

    # Initialize scheduler service
    logger.info("Initializing pipeline scheduler")
    scheduler_service = SchedulerService(
        pipeline_registry=pipeline_registry,
        orchestrator=orchestrator
    )
    await scheduler_service.start()

    # Store in app state
    app.state.scheduler_service = scheduler_service
    logger.info("Pipeline scheduler initialized")

    logger.info("✅ FlexLink Middleware started successfully")

    yield

    # Shutdown
    logger.info("Shutting down FlexLink Middleware...")

    # Shutdown scheduler
    if hasattr(app.state, 'scheduler_service'):
        await app.state.scheduler_service.shutdown()
    if http_client:
        await http_client.aclose()
        logger.info("HTTP client closed")

    logger.info("✅ FlexLink Middleware shut down successfully")


# Create FastAPI application
app = FastAPI(
    title="FlexLink Middleware",
    description="Flexible REST & File Integration Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Add middleware (order matters: first added = outermost = runs first)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(routes.router)
app.include_router(files.router)
app.include_router(health.router)
app.include_router(pipelines.router)


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint.

    Returns:
        Welcome message with API information
    """
    return {
        "message": "FlexLink Middleware API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
