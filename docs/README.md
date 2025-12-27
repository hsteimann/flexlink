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
- [Design Principles](architecture/design-principles.md) - Architectural decisions and rationale

### Features

#### Connectors
- [Connector Architecture](features/connectors/README.md) - How connectors work
- [PriceEdge Connector](connectors/priceedge.md) - Example REST integration

#### Data Processing
- [Transformation Engine](features/transformation-engine.md) - YAML-based data mapping
- [Pipeline Orchestration](features/pipeline-orchestration.md) - Multi-step workflow management

### Configuration

- [Configuration Overview](configuration/overview.md) - How configuration works

### How-To Guides

- [Weekday 08:00 Product Pricing Pipeline](how-to/scheduled-pipeline-example.md) - End-to-end example: REST → enrich → price lookup → DB

## Quick Navigation

**New to FlexLink?** Start with the [Architecture Overview](architecture/overview.md)

**Need to understand a specific feature?** Browse the [Features](features/) section

**Configuring FlexLink?** Check the [Configuration Guide](configuration/overview.md)

## Current vs Roadmap

- **Current (v0.3.x)**: REST/File/Webhook connectors, PriceEdge example, transformation engine, route processing, pipeline orchestration (extract/transform/load), basic scheduling in UTC.
- **Roadmap (v0.4.x+)**: Connector additions, richer pipeline features (validation step, background runs, more scheduler options), expanded docs for individual connectors and config flavors.

## Version

This documentation covers FlexLink v0.3.x (current) with references to v0.4.0 (planned features).

---

**Note**: This documentation focuses on architectural concepts and design decisions, not implementation details. For API references and code-level documentation, see the inline code documentation and README.md in the project root.
