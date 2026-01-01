# FlexLink Developer Documentation

Welcome to the FlexLink developer documentation. This guide provides an architectural overview and explains the design decisions behind FlexLink's main features.

## What is FlexLink?

FlexLink is an ETL (Extract, Transform, Load) middleware that provides a flexible, declarative approach to data integration. It enables you to:

- **Extract** data from various sources (REST APIs, files)
- **Transform** data using YAML-defined mappings
- **Load** data to multiple destinations (databases, webhooks, files)
- **Orchestrate** complex multi-step pipelines

## Documentation Structure

### Architecture

- [Overview](architecture/overview.md) - High-level architecture and core concepts
- [Architecture Diagrams](architecture/flexlink-architecture-diagram.md) - Visual system architecture and data flows
- [Design Principles](architecture/design-principles.md) - Architectural decisions and rationale
- [Component Architecture](architecture/components.md) - Detailed component breakdown
- [Data Flow](architecture/data-flow.md) - How data moves through the system

### Features

#### Connectors
- [Connector Architecture](features/connectors/README.md) - How connectors work
- [REST Connector](features/connectors/rest-connector.md) - HTTP API integration
- [File Connector](features/connectors/file-connector.md) - File-based data processing
- [Webhook Connector](features/connectors/webhook-connector.md) - Event delivery and notifications
- [Database Connector](features/connectors/database-connector.md) - PostgreSQL persistence
- [PriceEdge Connector](connectors/priceedge.md) - Example REST integration

#### Data Processing
- [Transformation Engine](features/transformation-engine.md) - YAML-based data mapping
- [Validation System](features/validation-system.md) - Data validation rules and error handling
- [Pipeline Orchestration](features/pipeline-orchestration.md) - Multi-step workflow management

### Configuration

- [Configuration Overview](configuration/overview.md) - How configuration works
- [Connector Configuration](configuration/connectors.md) - Configure data sources/destinations
- [Mapping Configuration](configuration/mappings.md) - Transformation rules
- [Route Configuration](configuration/routes.md) - Single-step flows
- [Pipeline Configuration](configuration/pipelines.md) - Multi-step workflows

### Guides

- [Mapping Summary](guides/MAPPING_SUMMARY.md) - Mapping configuration reference
- [Story Workflow Guide](guides/STORY_WORKFLOW_GUIDE.md) - Development workflow for user stories

### How-To Guides

- [Weekday 08:00 Product Pricing Pipeline](how-to/scheduled-pipeline-example.md) - End-to-end example: REST → enrich → price lookup → DB

## Quick Navigation

**New to FlexLink?** Start with the [Architecture Overview](architecture/overview.md)

**Need to understand a specific feature?** Browse the [Features](features/) section

**Configuring FlexLink?** Check the [Configuration Guide](configuration/overview.md)

**Looking for practical guidance?** See the [Guides](guides/) section

## Current vs Roadmap

- **Current (v0.4.2)**: REST/File/Webhook/Database connectors, specialized connector pattern (PriceEdge), transformation + validation engine, route processing, pipeline orchestration, background execution with run history, APScheduler-based cron/interval scheduling, and comprehensive test suite (685 tests, 71% coverage).
- **Roadmap**: See [docs/roadmap.md](roadmap.md) for the authoritative list of upcoming v0.5.0+ features.

## Version

This documentation covers FlexLink v0.4.2 (current) with references to v0.5.0+ (planned features).

---

**Note**: This documentation focuses on architectural concepts and design decisions, not implementation details. For API references and code-level documentation, see the inline code documentation and README.md in the project root.
