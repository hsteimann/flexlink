# FlexLink Middleware - Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL WORLD                                      │
│                                                                              │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐       │
│  │   Client     │         │ JSONPlaceh.  │         │  External    │       │
│  │ Applications │         │     API      │         │  REST APIs   │       │
│  │ (REST/Files) │         │              │         │              │       │
│  └──────┬───────┘         └──────▲───────┘         └──────▲───────┘       │
│         │                        │                         │               │
└─────────┼────────────────────────┼─────────────────────────┼───────────────┘
          │                        │                         │
          │ HTTP Requests          │ HTTP Requests           │
          │ File Uploads           │                         │
          │                        │                         │
          ▼                        │                         │
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FLEXLINK MIDDLEWARE PLATFORM                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                         API LAYER (FastAPI)                         │    │
│  │                                                                     │    │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │    │
│  │  │   Health    │  │   REST       │  │   File Routes            │ │    │
│  │  │   Routes    │  │   Routes     │  │                          │ │    │
│  │  │             │  │              │  │  • POST /files/upload    │ │    │
│  │  │ /health     │  │ /integrate   │  │  • POST /files/convert   │ │    │
│  │  │ /health/    │  │              │  │  • GET /files/download   │ │    │
│  │  │ connectors  │  │              │  │                          │ │    │
│  │  └─────────────┘  └──────┬───────┘  └────────┬─────────────────┘ │    │
│  │                          │                   │                     │    │
│  └──────────────────────────┼───────────────────┼─────────────────────┘    │
│                             │                   │                          │
│                             │                   │                          │
│  ┌──────────────────────────┼───────────────────┼─────────────────────┐   │
│  │                MIDDLEWARE LAYER              │                      │   │
│  │                                              │                      │   │
│  │  ┌─────────────────┐    ┌──────────────────┐│                      │   │
│  │  │ Logging         │    │ Error Handler    ││                      │   │
│  │  │ Middleware      │    │ Middleware       ││                      │   │
│  │  │                 │    │                  ││                      │   │
│  │  │ • Correlation   │    │ • Exception      ││                      │   │
│  │  │   IDs           │    │   Handling       ││                      │   │
│  │  │ • Request/      │    │ • HTTP Status    ││                      │   │
│  │  │   Response Log  │    │   Mapping        ││                      │   │
│  │  └─────────────────┘    └──────────────────┘│                      │   │
│  │                                              │                      │   │
│  └──────────────────────────┬───────────────────┼──────────────────────┘   │
│                             │                   │                          │
│                             ▼                   ▼                          │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        CORE LAYER                                    │  │
│  │                                                                      │  │
│  │  ┌──────────────┐      ┌──────────────┐      ┌──────────────────┐  │  │
│  │  │   Router     │      │ Transformer  │      │     Registry     │  │  │
│  │  │              │      │              │      │                  │  │  │
│  │  │ • Route      │      │ • Field      │      │ • Connector      │  │  │
│  │  │   Matching   │◄────►│   Mapping    │      │   Registration   │  │  │
│  │  │ • Connector  │      │ • Nested     │      │ • Lifecycle      │  │  │
│  │  │   Selection  │      │   Fields     │      │   Management     │  │  │
│  │  │ • Transform  │      │ • Transform  │      │ • Lookup         │  │  │
│  │  │   Orchestr.  │      │   Functions  │      │                  │  │  │
│  │  └──────┬───────┘      └──────────────┘      └────────┬─────────┘  │  │
│  │         │                                              │            │  │
│  └─────────┼──────────────────────────────────────────────┼────────────┘  │
│            │                                              │               │
│            │ get_connector()                              │               │
│            └──────────────────────────────────────────────┘               │
│            │                                                               │
│            ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      CONNECTOR LAYER                                 │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │            BaseConnector (Abstract)                          │   │  │
│  │  │                                                              │   │  │
│  │  │  • send_request()    • transform_request()                  │   │  │
│  │  │  • receive_response() • transform_response()                │   │  │
│  │  └──────────────────┬───────────────────────┬───────────────────┘   │  │
│  │                     │                       │                       │  │
│  │         ┌───────────┴───────────┐    ┌──────┴────────────┐         │  │
│  │         ▼                       ▼    ▼                    ▼         │  │
│  │  ┌──────────────┐      ┌─────────────────┐      ┌──────────────┐   │  │
│  │  │    REST      │      │ JSONPlaceholder │      │     File     │   │  │
│  │  │  Connector   │      │   Connector     │      │  Connector   │   │  │
│  │  │              │      │                 │      │              │   │  │
│  │  │ • HTTP       │      │ (extends REST)  │      │ • Upload     │   │  │
│  │  │   Methods    │      │                 │      │ • Convert    │   │  │
│  │  │ • Auth       │      │ • Custom        │      │ • Process    │   │  │
│  │  │   (Bearer,   │      │   transform     │      │              │   │  │
│  │  │   Basic,     │      │ • Demo API      │      │              │   │  │
│  │  │   API Key)   │      │                 │      │              │   │  │
│  │  │ • Retry      │      │                 │      │              │   │  │
│  │  │   Logic      │      │                 │      │              │   │  │
│  │  └──────┬───────┘      └────────┬────────┘      └──────┬───────┘   │  │
│  │         │                       │                      │           │  │
│  └─────────┼───────────────────────┼──────────────────────┼───────────┘  │
│            │                       │                      │              │
│            │ httpx.AsyncClient     │                      │              │
│            └───────────────────────┘                      │              │
│                                                           │              │
│                                            ┌──────────────┘              │
│                                            ▼                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      PARSER LAYER                                   │  │
│  │                                                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │            ParserFactory                                      │  │  │
│  │  │                                                               │  │  │
│  │  │  • get_parser(format)  • Auto-detect format                  │  │  │
│  │  └──────────────────┬────────────────────────────────────────────┘  │  │
│  │                     │                                               │  │
│  │         ┌───────────┼───────────┬───────────────┐                  │  │
│  │         ▼           ▼           ▼               ▼                  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐  ┌──────────┐            │  │
│  │  │   CSV    │ │   JSON   │ │   XML    │  │  Base    │            │  │
│  │  │  Parser  │ │  Parser  │ │  Parser  │  │  Parser  │            │  │
│  │  │          │ │          │ │          │  │ (Abstract)│           │  │
│  │  │ • parse  │ │ • parse  │ │ • parse  │  │          │            │  │
│  │  │   (bytes │ │   (bytes │ │   (bytes │  │ • parse()│            │  │
│  │  │   →DF)   │ │   →DF)   │ │   →DF)   │  │ • generate()│         │  │
│  │  │ • gen    │ │ • gen    │ │ • gen    │  │ • validate()│         │  │
│  │  │   (DF→   │ │   (DF→   │ │   (DF→   │  │          │            │  │
│  │  │   bytes) │ │   bytes) │ │   bytes) │  │          │            │  │
│  │  └──────────┘ └──────────┘ └──────────┘  └──────────┘            │  │
│  │         │           │           │                                  │  │
│  │         └───────────┴───────────┘                                  │  │
│  │                     │                                              │  │
│  │                     ▼                                              │  │
│  │            pandas.DataFrame                                       │  │
│  │         (Unified data format)                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      DATA MODELS LAYER (Pydantic)                   │  │
│  │                                                                     │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │  │
│  │  │  Connector   │  │ Integration  │  │  File Models             │ │  │
│  │  │   Models     │  │   Models     │  │                          │ │  │
│  │  │              │  │              │  │  • FileFormat (enum)     │ │  │
│  │  │ • Connector  │  │ • Request    │  │  • FileUploadRequest     │ │  │
│  │  │   Config     │  │ • Response   │  │  • FileProcessingResult  │ │  │
│  │  │ • AuthConfig │  │              │  │                          │ │  │
│  │  │ • RouteConfig│  │              │  │                          │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘ │  │
│  │                                                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  Transformation Models                                        │  │  │
│  │  │                                                               │  │  │
│  │  │  • TransformationRule  • RouteConfig                          │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                   CONFIGURATION LAYER                               │  │
│  │                                                                     │  │
│  │  ┌──────────────┐         ┌──────────────────────────────────┐    │  │
│  │  │   Settings   │         │  Connector Configs (YAML)        │    │  │
│  │  │              │         │                                  │    │  │
│  │  │ • App config │         │  • rest_generic.yaml             │    │  │
│  │  │ • Env vars   │         │  • jsonplaceholder.yaml          │    │  │
│  │  │ • File size  │         │  • file_processor.yaml           │    │  │
│  │  │   limits     │         │                                  │    │  │
│  │  └──────────────┘         └──────────────────────────────────┘    │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                   INFRASTRUCTURE LAYER                              │  │
│  │                                                                     │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │  │
│  │  │ httpx.Async  │  │   Logging    │  │  File Storage            │ │  │
│  │  │   Client     │  │              │  │                          │ │  │
│  │  │              │  │ • Structured │  │  • data/uploads/         │ │  │
│  │  │ • Connection │  │   JSON logs  │  │  • data/downloads/       │ │  │
│  │  │   Pooling    │  │ • Correlation│  │  • Temp cleanup          │ │  │
│  │  │ • Lifecycle  │  │   IDs        │  │                          │ │  │
│  │  │   (lifespan) │  │              │  │                          │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagrams

### Flow 1: REST Integration Request

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ POST /api/v1/integrate
     │ {route, method, body}
     │
     ▼
┌─────────────────┐
│ Logging         │  ← Add correlation ID
│ Middleware      │  ← Log incoming request
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ REST Routes     │  ← Parse request
│ /integrate      │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│    Router       │  ← Match route to connector
│                 │  ← Get route config
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  Transformer    │  ← Apply request transformations
│                 │  ← Map fields: source → target
│                 │  ← Apply functions: upper, lower, etc.
└────┬────────────┘
     │
     │ Transformed data
     │
     ▼
┌─────────────────┐
│   Registry      │  ← Get connector instance
│                 │  ← "jsonplaceholder" → JSONPlaceholderConnector
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ JSONPlaceholder │  ← Connector-specific logic
│   Connector     │
└────┬────────────┘
     │
     │ send_request()
     │
     ▼
┌─────────────────┐
│ REST Connector  │  ← Add auth headers
│  (Base)         │  ← Retry logic
└────┬────────────┘
     │
     │ HTTP Request
     │
     ▼
┌─────────────────┐
│ httpx.Async     │  ← Connection pooling
│   Client        │  ← Async I/O
└────┬────────────┘
     │
     │ HTTPS
     │
     ▼
┌─────────────────┐
│ JSONPlaceholder │
│      API        │
└────┬────────────┘
     │
     │ Response
     │
     ▼
┌─────────────────┐
│ REST Connector  │  ← Parse response
│                 │  ← Handle errors
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  Transformer    │  ← Apply response transformations
│                 │  ← Map fields back
└────┬────────────┘
     │
     │ Transformed response
     │
     ▼
┌─────────────────┐
│ Logging         │  ← Log response
│ Middleware      │  ← Include correlation ID
└────┬────────────┘
     │
     │ JSON Response
     │
     ▼
┌──────────┐
│  Client  │
└──────────┘
```

### Flow 2: File Upload & Conversion

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ POST /files/convert
     │ file=sample.csv
     │ target_format=json
     │
     ▼
┌─────────────────┐
│ Logging         │  ← Add correlation ID
│ Middleware      │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ File Routes     │  ← Receive UploadFile
│ /files/convert  │  ← Validate size (<10MB)
└────┬────────────┘
     │
     │ await file.read()
     │
     ▼
┌─────────────────┐
│ File Connector  │  ← Orchestrate conversion
└────┬────────────┘
     │
     │ Detect format (CSV)
     │
     ▼
┌─────────────────┐
│ ParserFactory   │  ← get_parser(FileFormat.CSV)
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│   CSV Parser    │  ← parse(bytes)
│                 │  ← pd.read_csv()
└────┬────────────┘
     │
     │ DataFrame
     │ ┌─────┬──────┬───────┐
     │ │ id  │ name │ email │
     │ ├─────┼──────┼───────┤
     │ │ 1   │ John │ j@... │
     │ │ 2   │ Jane │ ja... │
     │ └─────┴──────┴───────┘
     │
     ▼
┌─────────────────┐
│  Transformer    │  ← Apply transformations (optional)
│  (if requested) │  ← Field mapping, functions
└────┬────────────┘
     │
     │ Transformed DataFrame
     │
     ▼
┌─────────────────┐
│ ParserFactory   │  ← get_parser(FileFormat.JSON)
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  JSON Parser    │  ← generate(DataFrame)
│                 │  ← df.to_json(orient='records')
└────┬────────────┘
     │
     │ JSON bytes
     │ [{"id":1,"name":"John",...},
     │  {"id":2,"name":"Jane",...}]
     │
     ▼
┌─────────────────┐
│ File Connector  │  ← Save to data/downloads/
│                 │  ← Generate filename
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ File Routes     │  ← Return FileProcessingResult
│                 │  ← Schedule cleanup (BackgroundTasks)
└────┬────────────┘
     │
     │ Response: {success, download_url, ...}
     │
     ▼
┌──────────┐
│  Client  │  ← GET /files/download/{filename}
└────┬─────┘
     │
     ▼
┌─────────────────┐
│ File Routes     │  ← FileResponse
│ /download       │  ← Stream file
└────┬────────────┘
     │
     │ File bytes
     │
     ▼
┌──────────┐
│  Client  │
└──────────┘
     │
     │ (Background cleanup deletes temp file)
     │
     ▼
┌─────────────────┐
│ BackgroundTasks │  ← cleanup_file()
│                 │  ← os.remove()
└─────────────────┘
```

## Component Interactions Matrix

| Component      | Interacts With           | Interaction Type | Data Exchanged              |
|----------------|--------------------------|------------------|-----------------------------|
| **API Routes** | Middleware               | Layer            | HTTP Request/Response       |
| **API Routes** | Router                   | Function Call    | IntegrationRequest          |
| **API Routes** | File Connector           | Function Call    | UploadFile, FileFormat      |
| **Router**     | Registry                 | Lookup           | Connector name → Instance   |
| **Router**     | Transformer              | Function Call    | Data + TransformationRules  |
| **Router**     | Connector (via Registry) | Function Call    | Transformed request data    |
| **Transformer**| None (pure functions)    | N/A              | Data + Rules → Transformed  |
| **Registry**   | All Connectors           | Instantiation    | ConnectorConfig → Instance  |
| **Registry**   | Configuration            | Load             | YAML configs → Models       |
| **REST Conn**  | httpx.AsyncClient        | HTTP Call        | HTTP Request/Response       |
| **REST Conn**  | Transformer              | Function Call    | Request/Response data       |
| **File Conn**  | ParserFactory            | Function Call    | FileFormat → Parser         |
| **File Conn**  | Parsers                  | Function Call    | bytes ↔ DataFrame           |
| **Parsers**    | pandas                   | Library Call     | bytes → DataFrame → bytes   |
| **Config**     | Pydantic Models          | Validation       | YAML/Env → Validated Config |

## Event Flow & Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                    APPLICATION LIFECYCLE                             │
└─────────────────────────────────────────────────────────────────────┘

1. STARTUP (lifespan)
   ┌────────────────┐
   │ FastAPI App    │  create_app()
   │ Initialized    │
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Load Settings  │  Pydantic Settings from .env
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Create httpx   │  httpx.AsyncClient(timeout, limits)
   │ AsyncClient    │
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Initialize     │  ConnectorRegistry()
   │ Registry       │
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Load Connector │  Load YAML configs
   │ Configs        │  config/connectors/*.yaml
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Instantiate    │  RestConnector, JSONPlaceholderConnector,
   │ Connectors     │  FileConnector
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Register       │  Add to registry
   │ Middleware     │  Logging, ErrorHandler
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Mount Routers  │  /health, /api/v1, /files
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Server Ready   │  uvicorn starts listening
   └────────────────┘

2. REQUEST HANDLING (per request)
   ┌────────────────┐
   │ HTTP Request   │
   │ Received       │
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Logging        │  Generate correlation ID
   │ Middleware     │  Log request
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Route Handler  │  Execute endpoint function
   │ Executes       │
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Business Logic │  Router → Transformer → Connector
   │ Processes      │  OR File processing
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Response       │  Build response model
   │ Generated      │
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Logging        │  Log response
   │ Middleware     │  Include correlation ID
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ HTTP Response  │
   │ Sent           │
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Background     │  Cleanup temp files (if any)
   │ Tasks Execute  │
   └────────────────┘

3. SHUTDOWN (lifespan)
   ┌────────────────┐
   │ Shutdown       │
   │ Signal         │
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Close httpx    │  await client.aclose()
   │ AsyncClient    │
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Cleanup        │  Close connections
   │ Resources      │
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │ Server Stopped │
   └────────────────┘
```

## Error Handling Flow

```
┌──────────────┐
│ Error Occurs │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Error Type?                     │
└─────────────────────────────────────────┘
       │
       ├─── Validation Error (Pydantic)
       │    │
       │    ▼
       │    ┌────────────────────┐
       │    │ Error Handler      │
       │    │ Returns HTTP 422   │
       │    │ with details       │
       │    └────────────────────┘
       │
       ├─── HTTP 4xx (Client Error)
       │    │
       │    ▼
       │    ┌────────────────────┐
       │    │ NO RETRY           │
       │    │ Return error       │
       │    │ to client          │
       │    └────────────────────┘
       │
       ├─── HTTP 5xx (Server Error)
       │    │
       │    ▼
       │    ┌────────────────────┐
       │    │ Retry Logic        │
       │    │ (exponential       │
       │    │  backoff)          │
       │    └────────┬───────────┘
       │             │
       │             ├─ Success → Continue
       │             │
       │             └─ All retries failed
       │                 │
       │                 ▼
       │         ┌────────────────────┐
       │         │ Error Handler      │
       │         │ Returns HTTP 502   │
       │         └────────────────────┘
       │
       ├─── Timeout Error
       │    │
       │    ▼
       │    ┌────────────────────┐
       │    │ Retry with         │
       │    │ exponential        │
       │    │ backoff            │
       │    └────────┬───────────┘
       │             │
       │             └─ Failed → HTTP 504
       │
       ├─── File Too Large
       │    │
       │    ▼
       │    ┌────────────────────┐
       │    │ Return HTTP 413    │
       │    └────────────────────┘
       │
       ├─── Unsupported Format
       │    │
       │    ▼
       │    ┌────────────────────┐
       │    │ Return HTTP 400    │
       │    └────────────────────┘
       │
       └─── Unexpected Error
            │
            ▼
            ┌────────────────────┐
            │ Error Handler      │
            │ Log with trace     │
            │ Return HTTP 500    │
            └────────────────────┘
            │
            ▼
            ┌────────────────────┐
            │ Logged with        │
            │ correlation ID     │
            │ for debugging      │
            └────────────────────┘
```

## Key Architectural Patterns

### 1. Layered Architecture
- **API Layer**: FastAPI routes (HTTP interface)
- **Middleware Layer**: Cross-cutting concerns (logging, errors)
- **Core Layer**: Business logic (router, transformer, registry)
- **Connector Layer**: External system integration
- **Infrastructure Layer**: HTTP clients, file storage, logging

### 2. Dependency Injection
```
FastAPI lifespan
    ↓
Create shared resources (httpx client, registry)
    ↓
Store in app.state
    ↓
Inject into route handlers via Depends()
    ↓
Routes access shared instances (no globals)
```

### 3. Plugin Architecture (Connector Pattern)
```
BaseConnector (abstract)
    ↓
Concrete implementations (REST, File, etc.)
    ↓
Registry manages instances
    ↓
Router selects at runtime
    ↓
Extensible: add new connectors without changing core
```

### 4. Factory Pattern (Parsers)
```
ParserFactory
    ↓
get_parser(format) → appropriate parser
    ↓
All parsers share common interface
    ↓
File Connector agnostic to format details
```

### 5. Strategy Pattern (Transformation)
```
TransformationRule (declarative)
    ↓
Transformer applies rules
    ↓
Different transformation strategies
    ↓
Extensible: add new transformation functions
```

## Scalability Considerations

```
┌─────────────────────────────────────────────────────────────┐
│                   SINGLE INSTANCE                            │
│                                                              │
│  ┌──────────────┐                                           │
│  │  FlexLink    │                                           │
│  │  FastAPI     │                                           │
│  │  Instance    │                                           │
│  └──────────────┘                                           │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐                                           │
│  │  In-Memory   │                                           │
│  │  File Storage│                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                        ▼
                (Scale Horizontally)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                HORIZONTAL SCALING (Phase 2)                  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  FlexLink    │  │  FlexLink    │  │  FlexLink    │     │
│  │  Instance 1  │  │  Instance 2  │  │  Instance N  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            ▼                                │
│                  ┌──────────────────┐                       │
│                  │   Load Balancer  │                       │
│                  └──────────────────┘                       │
│                            │                                │
│         ┌──────────────────┼──────────────────┐            │
│         ▼                  ▼                  ▼            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Shared     │  │   Message    │  │   Shared     │    │
│  │   Storage    │  │   Queue      │  │   Cache      │    │
│  │  (S3/MinIO)  │  │  (RabbitMQ)  │  │   (Redis)    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack Summary

| Layer          | Technology        | Purpose                           |
|----------------|-------------------|-----------------------------------|
| Web Framework  | FastAPI           | Async REST API, auto-docs         |
| HTTP Client    | httpx             | Async HTTP calls to external APIs |
| Validation     | Pydantic V2       | Data models, settings, validation |
| File Processing| pandas            | Parse/generate CSV/JSON/XML       |
| XML Parsing    | lxml              | High-performance XML support      |
| Server         | Uvicorn           | ASGI server for FastAPI           |
| Testing        | pytest            | Unit & integration tests          |
| Testing (HTTP) | respx             | Mock httpx requests               |
| Linting        | ruff              | Fast Python linter & formatter    |
| Type Checking  | mypy              | Static type checking              |
| Config         | PyYAML            | YAML config file parsing          |
| Containerization| Docker           | Deployment & portability          |

---

**Legend:**
- `→` : Data flow direction
- `├─` : Branch/alternative path
- `▼` : Sequential flow down
- `◄►` : Bidirectional interaction
- `[ ]` : Component/module
- `( )` : Process/action
