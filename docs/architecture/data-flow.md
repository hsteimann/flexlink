# Data Flow

This describes how requests travel through FlexLink from HTTP entry to downstream systems.

## Simple Route (single connector)

1) **HTTP request** hits `/api/v1/route` with route, method, body.
2) **Request Router** matches `RouteConfig` (path/method).
3) **Transform** (optional): Applies mapping/validation if configured.
4) **Connector call**: Sends request via target connector (REST/file/webhook/db).
5) **Response transform** (optional): Applies response transformations.
6) **Return** transformed response to caller.

## Pipeline (multi-step)

1) **Trigger**: API call `/api/v1/pipelines/{name}/run` or scheduler.
2) **Load config**: PipelineRegistry returns `PipelineConfig`.
3) **Create context**: Run ID, timestamps, empty data/metadata/errors.
4) **Step loop**:
   - Extract: connector fetch → `context.data`.
   - Transform: mapping + optional validation → mutate `context.data`.
   - Load: writes out (per record or batch) using connector.
   - Errors handled per-step (`fail_pipeline`, `skip_step`, `continue`) with retry/backoff.
5) **Result**: Orchestrator returns `PipelineExecutionResult` with step statuses and metadata.

## Scheduling

- APScheduler starts on app startup.
- For each pipeline with `schedule.enabled`, registers cron/interval job (UTC).
- Job callback calls `PipelineOrchestrator.execute_pipeline`.

## Configuration Flow

- On startup, connectors and routes load from `config/`.
- Pipelines load at startup and can be reloaded via registry.
- Mappings/validation load on-demand by transform steps or routes.
