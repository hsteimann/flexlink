# FlexLink Roadmap

Authoritative roadmap reference for the FlexLink middleware project. Use this document as the single source of truth for current release scope and upcoming milestones.

## Current Release: v0.4.2

- Specialized connector architecture (PriceEdgeConnector + name-first registry lookup)
- REST/File/Webhook/PostgreSQL connectors with authentication, retry logic, and batching
- Background pipeline execution with TaskManager, `/runs/{run_id}` polling, and log streaming
- Cron/interval scheduling via APScheduler plus SQLite-backed run history auditing
- Pipeline orchestration with per-step error strategies, pagination, and data validation
- Transformation/mapping engine with declarative YAML configurations
- File-to-REST/File-to-Database workflows, async file persistence, and format conversions
- Dockerized deployment, FastAPI docs, health endpoints, and a 685-test suite with 71% coverage

## Upcoming: v0.5.0 (In Planning)

Scope is being re-evaluated for the next minor release. Candidate items include:

- Message queue connectors (RabbitMQ, Kafka, SQS) for event streaming
- Advanced data mapping (JSONata expressions, custom Python modules)
- Large file streaming, chunked processing, and additional formats (Parquet, Excel, Avro)
- Enhanced observability (Prometheus metrics, OpenTelemetry tracing, dashboard templates)
- Circuit breaker patterns, caching/response buffering, API rate limiting, and API key auth
- Additional connectors (GraphQL, SOAP, gRPC, WebSocket) as demand solidifies

## Future (v0.6.0+ / Enterprise Track)

- Distributed pipeline execution (Celery/Dramatiq or similar)
- Multi-database transactions and advanced persistence options
- Multi-tenancy, audit logging, and admin UI enhancements
- Deep monitoring integrations and enterprise security hardening

## References

- Product Requirement Plans (PRPs): see `PRPs/active/flexlink-middleware-mvp-PHASE2.md` for detailed breakdowns
- Main README: [`../README.md`](../README.md) – include only summary bullets and link back here
- Architecture Docs: when referencing roadmap items, link to this file instead of restating bullet lists
