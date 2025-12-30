"""FlexLink Middleware FastAPI Application."""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from flexlink.api import connectors, dependencies, files, health, mappings, pipelines, routes
from flexlink.config import get_settings, load_route_configs
from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.router import RequestRouter
from flexlink.core.run_history import RunHistoryStorage
from flexlink.core.scheduler_service import SchedulerService
from flexlink.core.task_manager import TaskManager
from flexlink.core.transformation import TransformationEngine
from flexlink.middleware.error_handling import ErrorHandlingMiddleware
from flexlink.middleware.logging import LoggingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# Filter out NiceGUI's harmless "Request is not set" errors
class NiceGUIErrorFilter(logging.Filter):
    """Filter out NiceGUI's prune_user_storage RuntimeError logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out 'Request is not set' errors from NiceGUI timer."""
        if record.name == "nicegui" and record.levelname == "ERROR":
            if "Request is not set" in record.getMessage():
                return False  # Suppress this specific error
        return True


# Apply filter to nicegui logger
nicegui_logger = logging.getLogger("nicegui")
nicegui_logger.addFilter(NiceGUIErrorFilter())

# Global instances
http_client: httpx.AsyncClient | None = None
settings = get_settings()  # Load settings at module level for UI initialization


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

    # Initialize run history storage first (needed by TaskManager and SchedulerService)
    logger.info("Initializing run history storage")
    run_history = RunHistoryStorage(db_path="data/run_history.db")
    await run_history.initialize()
    app.state.run_history = run_history
    logger.info("Run history storage initialized")

    # Initialize task manager for background execution
    logger.info("Initializing task manager")
    task_manager = TaskManager(run_history=run_history)
    app.state.task_manager = task_manager
    logger.info("Task manager initialized")

    # Initialize scheduler service
    logger.info("Initializing pipeline scheduler")
    scheduler_service = SchedulerService(
        pipeline_registry=pipeline_registry,
        orchestrator=orchestrator,
        run_history=run_history
    )
    await scheduler_service.start()

    # Store in app state
    app.state.scheduler_service = scheduler_service
    logger.info("Pipeline scheduler initialized")

    logger.info("✅ FlexLink Middleware started successfully")

    yield

    # Shutdown
    logger.info("Shutting down FlexLink Middleware...")

    # Cleanup task manager
    if hasattr(app.state, 'task_manager'):
        app.state.task_manager.cleanup_completed_tasks()
        logger.info("Task manager cleaned up")

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
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add middleware (order matters: first added = outermost = runs first)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)

# Include routers with /api prefix
app.include_router(routes.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(pipelines.router, prefix="/api")
app.include_router(connectors.router, prefix="/api")
app.include_router(mappings.router, prefix="/api")

# API info endpoint
@app.get("/api")
async def api_root() -> dict[str, str]:
    """
    API root endpoint.

    Returns:
        API information and available endpoints
    """
    return {
        "message": "FlexLink Middleware API",
        "version": "0.1.0",
        "docs": "/api/docs",
        "redoc": "/api/redoc",
        "health": "/api/health",
        "ui": "/",
    }


# Initialize UI (NiceGUI)
# UI routes: /, /pipelines, /monitoring/{run_id}, /history, etc.
try:
    from nicegui import ui

    from flexlink.ui import create_ui_app

    # Initialize UI with Material Design 3 theme and routes
    # API base URL includes /api prefix (new architecture)
    create_ui_app(api_base_url="http://localhost:8000/api")

    # Attach NiceGUI to FastAPI app at root
    # Use secret key from settings for storage encryption
    ui.run_with(app, mount_path="/", storage_secret=settings.ui_secret_key)
    logger.info("✅ FlexLink UI initialized at / (root)")
    logger.info("✅ FlexLink API available at /api")
except ImportError as e:
    logger.warning(f"UI not available: {e}")
    logger.info("API-only mode - UI disabled")
