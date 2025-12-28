# Component Architecture

This page summarizes FlexLink's major components and their responsibilities.

## Runtime Components

- **FastAPI App** (`flexlink.main`): Hosts HTTP endpoints, wiring dependencies, middleware, and routers.
- **Connector Registry** (`flexlink.core.registry.ConnectorRegistry`): Loads connector configs, instantiates connectors, provides lookup.
- **Request Router** (`flexlink.core.router.RequestRouter`): Matches inbound requests to configured routes, applies transformations, calls connectors.
- **Pipeline Registry** (`flexlink.core.pipeline_registry.PipelineRegistry`): Loads pipeline YAMLs and exposes validated configs.
- **Pipeline Orchestrator** (`flexlink.core.pipeline_orchestrator.PipelineOrchestrator`): Executes multi-step pipelines, manages context, retry, and error strategies.
- **Scheduler Service** (`flexlink.core.scheduler_service.SchedulerService`): Uses APScheduler to run pipelines on cron/interval triggers.
- **Transformation Engine** (`flexlink.core.transformation.TransformationEngine`): Applies mapping rules to records.
- **Validator** (`flexlink.core.validator.Validator`): Validates transformed data when mappings include validation rules.

## Connectors (examples)

- **REST** (`flexlink.connectors.rest_connector.RestConnector`): Async HTTP via `httpx`, supports auth headers, retries.
- **File** (`flexlink.connectors.file_connector.FileConnector`): Local file IO.
- **Webhook** (`flexlink.connectors.webhook_connector.WebhookConnector`): Sends outbound events.
- **PostgreSQL** (`flexlink.connectors.postgresql_connector.PostgreSQLConnector`): Database writes using asyncpg pool.

## Data Models

- **ConnectorConfig / DatabaseConnectorConfig / WebhookConfig**: Connector settings.
- **RouteConfig**: Request routing configuration.
- **PipelineConfig / PipelineStepConfig / RetryPolicy / ScheduleConfig**: Pipeline definitions.
- **MappingConfig / TransformationRule**: Transformation rules.
- **ValidationConfig / ValidationRule**: Data quality rules.

## Middleware

- **LoggingMiddleware**: Structured request logging.
- **ErrorHandlingMiddleware**: Normalizes exceptions to HTTP responses.

## Storage & Config Layout

- `config/connectors`: Connector definitions.
- `config/mappings`: Transformation + validation rules.
- `config/routes`: Route definitions.
- `config/pipelines`: Pipeline definitions.
