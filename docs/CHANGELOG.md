# Changelog

All notable changes to FlexLink Middleware will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.2] - December 2025

### Added
- **Specialized Connector Pattern**: New inheritance-based model that lets connectors declare API-specific behavior without complicating pipelines
- **PriceEdgeConnector**: First specialized connector with automatic response unwrapping, body-based pagination, and helper methods like `query_suggested_prices()`
- **Background Pipeline Execution**: Async TaskManager, `/runs/{run_id}` polling endpoint, and log streaming prevent long ETL jobs from blocking HTTP workers
- **Scheduling & Run History**: APScheduler-backed cron/interval execution with results persisted to SQLite history for audit trails
- **Name-First Registry Lookup**: Registry prioritizes connector names (e.g., `priceedge`) before falling back to generic types, keeping everything backwards compatible
- **65 Tests**: Connector and background-execution suites expanded (including 6 new PriceEdge tests) to maintain 100% coverage for these features

### Test Coverage
- 685 tests total (100% pass rate)
- 71% overall coverage
- 100% coverage on critical infrastructure components

## [0.4.1] - December 2025

### Added
- **Material Design 3 UI**: Modern web dashboard built with NiceGUI and Material You design system
- **Pipeline Monitoring**: View, execute, and monitor pipelines through an intuitive web interface
- **Real-time Status**: Live status updates for pipeline executions with auto-refresh
- **Execution History**: Browse historical pipeline runs with filtering and pagination
- **Run Logs**: View detailed execution logs with timestamp and severity filtering
- **Dark/Light Theme**: Automatic theme support with manual toggle
- **Responsive Design**: Mobile-friendly interface with Material Design 3 components
- **Custom Exceptions**: User-friendly error handling with specific exception types
- **57 Tests**: Comprehensive API client tests with 92% coverage on core components

## [0.4.0] - December 2025

### Added
- **Declarative Pipelines**: Define complete Extract → Transform → Load workflows in YAML configuration
- **Multi-Step Execution**: Chain multiple extraction, transformation, and load operations sequentially
- **Pagination Support**: Automatic data fetching with offset/limit, cursor, and page-based strategies
- **Batch Loading**: Efficient bulk data transfer with configurable batch sizes and partial failure handling
- **Retry Logic**: Exponential, linear, and fixed backoff strategies with jitter for failed steps
- **Error Handling**: Configurable strategies (fail pipeline, skip step, or continue) per step
- **HTTP API**: Execute pipelines via REST endpoints with real-time status and metrics
- **328 Tests**: Added 25 new tests for pipeline orchestration (steps, orchestrator, API) - all passing

## [0.3.1] - December 2025

### Added
- **Webhook Notifications**: New webhook connector sends HTTP POST notifications to external endpoints
- **HMAC Signatures**: HMAC-SHA256 signature generation for webhook security and payload verification
- **Multiple Auth Methods**: Support for Bearer tokens, API keys, Basic auth, and custom headers
- **Smart Retry Logic**: Exponential backoff with jitter for failed deliveries (configurable 1-10 attempts)
- **Error Handling**: Distinguishes 4xx (no retry) from 5xx (retry with backoff) responses
- **Statistics Tracking**: Monitor delivery success rates, attempt counts, and performance metrics
- **303 Tests**: Added 9 comprehensive webhook tests - all passing (100% coverage)

## [0.3.0] - December 2025

### Added
- **Database Persistence**: New PostgreSQL connector writes validated data directly to databases
- **Connection Pooling**: Production-ready connection management with configurable pool size (2-10 connections)
- **INSERT Operations**: Simplified MVP with INSERT support, parameterized queries for SQL injection protection
- **File-to-Database Pipeline**: Parse CSV/JSON/XML files and persist records directly to PostgreSQL
- **SSL/TLS Support**: Encrypted database connections with automatic sslmode configuration
- **294 Tests**: Added 24 new tests (11 model tests + 13 integration tests) - all passing

## [0.2.3] - December 2025

### Changed
- **Unified Connector Management**: File connector now registered in ConnectorRegistry like REST connectors
- **YAML Configuration**: File connector configurable via `config/connectors/file.yaml`
- **Consistent Architecture**: All connectors share same lifecycle and can be enabled/disabled via config
- **270 Tests**: All existing tests pass with new architecture

## [0.2.2] - December 2025

### Added
- **File-to-REST Pipeline**: New `/api/v1/files/forward` endpoint bridges file processing with routing/transformation pipeline
- **Batch Ingestion Workflows**: Parse files (CSV/JSON/XML) → Apply transformations → Forward to REST APIs
- **Dual Forwarding Modes**: Individual (one request per record) or batch (all records in one request)
- **Transformation Integration**: File records flow through route-level and connector-level transformations
- **270 Tests**: Added 5 comprehensive tests for file-to-REST forwarding with transformations

## [0.2.1] - December 2025

### Added
- **Async File Processing**: Upload endpoint now saves processed files for later download (default behavior)
- **Download Persistence**: New `GET /api/v1/files/download/{file_id}` endpoint for async file retrieval
- **File TTL Management**: Automatic 24-hour retention with cleanup endpoint for expired files
- **Flexible Upload Modes**: Choose between async download, validation only, or immediate file return
- **265 Tests**: Added 8 new tests for download persistence and cleanup functionality

## [0.2.0] - December 2025

### Added
- **HTTP Status Code Propagation**: Proper REST semantics with accurate status codes (404, 500, etc.)
- **Query Parameter Support**: GET/DELETE requests now properly use query strings instead of JSON bodies
- **Connector Transform Hooks**: Connectors can implement custom transformations for system-specific quirks
- **File Upload Returns Content**: Upload endpoint can now return processed file content (via `return_file` parameter)
- **Multi-Layer Transformations**: Route-level and connector-level transformations work together
- **257 Tests**: Comprehensive test coverage for all architectural improvements

## Future Releases

### [0.5.0] - In Planning

Scope is being redefined. The plan currently targets:

- Message queue connectors (RabbitMQ, Kafka) for event streaming
- Advanced data mapping (JSONata expressions)
- Streaming support for very large files (>10MB) and expanded file formats
- Additional connector types (GraphQL, SOAP, gRPC, WebSocket)
- Enhanced observability (OpenTelemetry, Prometheus) with dashboards/metrics
- Circuit breaker patterns, caching, and API rate limiting

### Enterprise Features


- Job scheduling (cron-based)
- State persistence (SQLite/PostgreSQL)
- Audit logging
- Multi-tenancy support
