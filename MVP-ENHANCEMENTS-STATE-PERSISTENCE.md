# MVP Enhancement: State Persistence & Retry Logic

## Overview
Add state persistence to track synchronization state, handle failed records, and implement intelligent retry logic for API hickups.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ FlexLink Middleware                                         │
│                                                             │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐ │
│  │  Scheduler   │─────▶│  Sync Jobs   │─────▶│   State  │ │
│  │  (APScheduler)│      │              │      │   Store  │ │
│  └──────────────┘      └──────────────┘      └──────────┘ │
│                              │                      │       │
│                              ▼                      │       │
│                        ┌──────────────┐            │       │
│                        │  Connectors  │            │       │
│                        │  (REST API)  │            │       │
│                        └──────────────┘            │       │
│                              │                      │       │
│                              │ (on success)         │       │
│                              └─────────────────────▶│       │
│                              │ (on failure)         │       │
│                              └─────────────────────▶│       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         │                                │
         ▼                                ▼
   ┌──────────┐                    ┌──────────┐
   │   PIM    │                    │ Shopware │
   │ (iPIM)   │                    │    ERP   │
   └──────────┘                    └──────────┘
```

## Implementation

### Option 1: SQLite (Recommended for MVP)
**Pros:**
- No external database required
- File-based, easy deployment
- Perfect for single-instance MVP
- Built into Python

**Cons:**
- Not suitable for multi-instance (without shared filesystem)
- Limited concurrent writes

### Option 2: PostgreSQL (Production)
**Pros:**
- Production-ready
- Multi-instance support
- Better concurrent performance

**Cons:**
- Requires external database setup

---

## Database Schema

```python
# src/flexlink/models/sync_state.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum

class SyncStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"

class SyncRecord(BaseModel):
    """Track individual record sync attempts"""
    id: Optional[int] = None
    job_id: str = Field(..., description="Job identifier (e.g., 'sync_products_pim')")
    record_type: str = Field(..., description="Type of record (e.g., 'product', 'order')")
    record_id: str = Field(..., description="External ID from source system")
    source_system: str = Field(..., description="Source connector name")
    target_system: str = Field(..., description="Target connector name")
    status: SyncStatus = SyncStatus.PENDING
    attempt_count: int = 0
    max_retries: int = 3
    last_attempt_at: Optional[datetime] = None
    last_error: Optional[str] = None
    payload: Optional[dict] = None  # Store failed payload for retry
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class JobExecution(BaseModel):
    """Track job execution history"""
    id: Optional[int] = None
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: SyncStatus
    records_processed: int = 0
    records_succeeded: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
```

---

## Database Layer (SQLite)

```python
# src/flexlink/db/database.py
import aiosqlite
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
from flexlink.models.sync_state import SyncRecord, SyncStatus, JobExecution

class SyncStateStore:
    def __init__(self, db_path: str = "data/flexlink.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """Initialize database schema"""
        async with aiosqlite.connect(self.db_path) as db:
            # Sync records table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sync_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    record_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    target_system TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    last_attempt_at TIMESTAMP,
                    last_error TEXT,
                    payload TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(job_id, record_id, source_system, target_system)
                )
            """)

            # Job executions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS job_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    status TEXT NOT NULL,
                    records_processed INTEGER DEFAULT 0,
                    records_succeeded INTEGER DEFAULT 0,
                    records_failed INTEGER DEFAULT 0,
                    error_message TEXT
                )
            """)

            # Indexes for performance
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_status
                ON sync_records(status, job_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_record_lookup
                ON sync_records(record_id, source_system, target_system)
            """)

            await db.commit()

    async def create_sync_record(self, record: SyncRecord) -> int:
        """Create or update a sync record"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO sync_records
                (job_id, record_type, record_id, source_system, target_system,
                 status, attempt_count, max_retries, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id, record_id, source_system, target_system)
                DO UPDATE SET
                    status = excluded.status,
                    attempt_count = excluded.attempt_count,
                    updated_at = excluded.updated_at
            """, (
                record.job_id, record.record_type, record.record_id,
                record.source_system, record.target_system, record.status.value,
                record.attempt_count, record.max_retries,
                str(record.payload) if record.payload else None,
                record.created_at, record.updated_at
            ))
            await db.commit()
            return cursor.lastrowid

    async def update_record_status(
        self,
        record_id: str,
        source_system: str,
        target_system: str,
        status: SyncStatus,
        error: Optional[str] = None
    ):
        """Update sync record status"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sync_records
                SET status = ?,
                    last_attempt_at = ?,
                    last_error = ?,
                    attempt_count = attempt_count + 1,
                    updated_at = ?
                WHERE record_id = ?
                  AND source_system = ?
                  AND target_system = ?
            """, (
                status.value,
                datetime.utcnow(),
                error,
                datetime.utcnow(),
                record_id,
                source_system,
                target_system
            ))
            await db.commit()

    async def get_failed_records(
        self,
        job_id: Optional[str] = None,
        max_retries_exceeded: bool = False
    ) -> List[SyncRecord]:
        """Get failed records for retry"""
        query = """
            SELECT * FROM sync_records
            WHERE status IN ('failed', 'retry')
        """
        params = []

        if job_id:
            query += " AND job_id = ?"
            params.append(job_id)

        if not max_retries_exceeded:
            query += " AND attempt_count < max_retries"

        query += " ORDER BY created_at ASC"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_sync_record(row) for row in rows]

    async def get_last_successful_sync(
        self,
        job_id: str
    ) -> Optional[datetime]:
        """Get timestamp of last successful job execution"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT completed_at FROM job_executions
                WHERE job_id = ? AND status = 'success'
                ORDER BY completed_at DESC
                LIMIT 1
            """, (job_id,)) as cursor:
                row = await cursor.fetchone()
                return datetime.fromisoformat(row[0]) if row else None

    async def create_job_execution(self, execution: JobExecution) -> int:
        """Create job execution record"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO job_executions
                (job_id, started_at, status, records_processed)
                VALUES (?, ?, ?, ?)
            """, (
                execution.job_id,
                execution.started_at,
                execution.status.value,
                execution.records_processed
            ))
            await db.commit()
            return cursor.lastrowid

    async def complete_job_execution(
        self,
        execution_id: int,
        status: SyncStatus,
        records_succeeded: int,
        records_failed: int,
        error_message: Optional[str] = None
    ):
        """Mark job execution as complete"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE job_executions
                SET completed_at = ?,
                    status = ?,
                    records_succeeded = ?,
                    records_failed = ?,
                    error_message = ?
                WHERE id = ?
            """, (
                datetime.utcnow(),
                status.value,
                records_succeeded,
                records_failed,
                error_message,
                execution_id
            ))
            await db.commit()

    def _row_to_sync_record(self, row) -> SyncRecord:
        """Convert database row to SyncRecord"""
        return SyncRecord(
            id=row['id'],
            job_id=row['job_id'],
            record_type=row['record_type'],
            record_id=row['record_id'],
            source_system=row['source_system'],
            target_system=row['target_system'],
            status=SyncStatus(row['status']),
            attempt_count=row['attempt_count'],
            max_retries=row['max_retries'],
            last_attempt_at=datetime.fromisoformat(row['last_attempt_at']) if row['last_attempt_at'] else None,
            last_error=row['last_error'],
            payload=eval(row['payload']) if row['payload'] else None,
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )
```

---

## Updated Sync Jobs with State Tracking

```python
# src/flexlink/jobs/sync_jobs.py (enhanced)
import logging
from flexlink.core.registry import ConnectorRegistry
from flexlink.db.database import SyncStateStore
from flexlink.models.sync_state import SyncRecord, SyncStatus, JobExecution
from datetime import datetime

logger = logging.getLogger(__name__)

async def sync_products_from_pim(
    registry: ConnectorRegistry,
    state_store: SyncStateStore
):
    """
    Job: Pull product changes from iPIM Novomind every 30 minutes
    With state tracking and retry logic
    """
    job_id = "sync_products_pim"
    logger.info(f"Starting {job_id}")

    # Create job execution record
    execution = JobExecution(
        job_id=job_id,
        started_at=datetime.utcnow(),
        status=SyncStatus.IN_PROGRESS
    )
    execution_id = await state_store.create_job_execution(execution)

    succeeded = 0
    failed = 0

    try:
        # Get connectors
        pim_connector = registry.get_connector("novomind_pim")
        shopware_connector = registry.get_connector("shopware6")

        # 1. Process failed records from previous runs (RETRY LOGIC)
        failed_records = await state_store.get_failed_records(job_id=job_id)
        logger.info(f"Retrying {len(failed_records)} failed products")

        for record in failed_records:
            try:
                # Retry with stored payload
                await shopware_connector.send_request(
                    method="POST",
                    path="/api/product",
                    json=record.payload
                )
                await state_store.update_record_status(
                    record.record_id,
                    record.source_system,
                    record.target_system,
                    SyncStatus.SUCCESS
                )
                succeeded += 1
                logger.info(f"✓ Retry succeeded for product {record.record_id}")

            except Exception as e:
                await state_store.update_record_status(
                    record.record_id,
                    record.source_system,
                    record.target_system,
                    SyncStatus.FAILED,
                    error=str(e)
                )
                failed += 1
                logger.warning(f"✗ Retry failed for product {record.record_id}: {str(e)}")

        # 2. Fetch new changed products from PIM
        response = await pim_connector.send_request(
            method="GET",
            path="/api/products/delta",
            params={"minutes": "30", "limit": "50"}
        )

        if response.status_code == 200:
            products = response.body.get("products", [])
            logger.info(f"Fetched {len(products)} new changed products from PIM")

            # 3. Process each product with state tracking
            for product in products:
                product_id = product.get("id")

                # Create sync record
                sync_record = SyncRecord(
                    job_id=job_id,
                    record_type="product",
                    record_id=product_id,
                    source_system="novomind_pim",
                    target_system="shopware6",
                    status=SyncStatus.PENDING
                )
                await state_store.create_sync_record(sync_record)

                try:
                    # Transform product data
                    transformed = await transform_pim_to_shopware(product)

                    # Send to Shopware (with built-in retry from connector)
                    await shopware_connector.send_request(
                        method="POST",
                        path="/api/product",
                        json=transformed
                    )

                    # Mark as success
                    await state_store.update_record_status(
                        product_id,
                        "novomind_pim",
                        "shopware6",
                        SyncStatus.SUCCESS
                    )
                    succeeded += 1
                    logger.info(f"✓ Synced product {product_id}")

                except Exception as e:
                    # Mark as failed, store payload for retry
                    sync_record.status = SyncStatus.FAILED
                    sync_record.payload = transformed
                    await state_store.create_sync_record(sync_record)
                    await state_store.update_record_status(
                        product_id,
                        "novomind_pim",
                        "shopware6",
                        SyncStatus.FAILED,
                        error=str(e)
                    )
                    failed += 1
                    logger.error(f"✗ Failed to sync product {product_id}: {str(e)}")

            # Complete job execution
            await state_store.complete_job_execution(
                execution_id,
                SyncStatus.SUCCESS,
                succeeded,
                failed
            )
            logger.info(f"Job completed: {succeeded} succeeded, {failed} failed")

        else:
            error_msg = f"PIM API returned status {response.status_code}"
            logger.error(error_msg)
            await state_store.complete_job_execution(
                execution_id,
                SyncStatus.FAILED,
                succeeded,
                failed,
                error_msg
            )

    except Exception as e:
        logger.error(f"Job {job_id} crashed: {str(e)}", exc_info=True)
        await state_store.complete_job_execution(
            execution_id,
            SyncStatus.FAILED,
            succeeded,
            failed,
            str(e)
        )


async def transform_pim_to_shopware(pim_product: dict) -> dict:
    """Transform iPIM product to Shopware format"""
    return {
        "id": pim_product.get("id"),
        "productNumber": pim_product.get("sku"),
        "name": pim_product.get("title"),
        "description": pim_product.get("description"),
        "price": [{
            "currencyId": "euro_id",
            "gross": pim_product.get("price"),
        }],
        "stock": pim_product.get("inventory", 0),
        "active": pim_product.get("is_active", True),
        # Handle media URLs
        "media": [
            {"url": url} for url in pim_product.get("image_urls", [])
        ],
        # Map other fields as needed
    }
```

---

## API Endpoints for Monitoring

```python
# src/flexlink/api/sync_routes.py
from fastapi import APIRouter, Depends, Request, Query
from typing import Optional
from flexlink.db.database import SyncStateStore

sync_router = APIRouter(prefix="/sync", tags=["sync"])

def get_state_store(request: Request) -> SyncStateStore:
    """Dependency injection for state store"""
    return request.app.state.state_store

@sync_router.get("/failed-records")
async def get_failed_records(
    job_id: Optional[str] = Query(None),
    state_store: SyncStateStore = Depends(get_state_store)
):
    """Get list of failed sync records"""
    failed = await state_store.get_failed_records(job_id=job_id)
    return {
        "count": len(failed),
        "records": [
            {
                "record_id": r.record_id,
                "record_type": r.record_type,
                "source": r.source_system,
                "target": r.target_system,
                "attempt_count": r.attempt_count,
                "last_error": r.last_error,
                "last_attempt": r.last_attempt_at.isoformat() if r.last_attempt_at else None
            }
            for r in failed
        ]
    }

@sync_router.get("/job-history/{job_id}")
async def get_job_history(
    job_id: str,
    limit: int = Query(10, le=100),
    state_store: SyncStateStore = Depends(get_state_store)
):
    """Get execution history for a job"""
    # Query job_executions table
    # Return last N executions with success/failure stats
    pass

@sync_router.post("/retry-failed")
async def retry_failed_records(
    job_id: Optional[str] = Query(None),
    request: Request = None
):
    """Manually trigger retry of failed records"""
    # Trigger the sync job manually
    pass
```

---

## Configuration

```yaml
# config/settings.yaml
database:
  path: "data/flexlink.db"
  connection_timeout: 30

sync:
  default_max_retries: 3
  retry_backoff_multiplier: 2  # 2^attempt seconds
  cleanup_successful_after_days: 30  # Archive old successful records
  cleanup_failed_after_days: 90
```

---

## Integration with Main App

```python
# src/flexlink/main.py
from flexlink.db.database import SyncStateStore

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Initialize state store
    state_store = SyncStateStore()
    await state_store.init_db()

    # Initialize other components
    http_client = httpx.AsyncClient(...)
    registry = ConnectorRegistry()
    await registry.load_connectors()

    # Start scheduler with state_store
    scheduler = JobScheduler()
    scheduler.add_job(
        func=sync_products_from_pim,
        cron_expression="*/30 * * * *",
        job_id="sync_products_pim",
        registry=registry,
        state_store=state_store  # Pass state store to job
    )
    scheduler.start()

    # Store in app state
    app.state.http_client = http_client
    app.state.registry = registry
    app.state.scheduler = scheduler
    app.state.state_store = state_store

    yield

    # Shutdown
    scheduler.shutdown()
    await http_client.aclose()
```

---

## Benefits

1. **Resilience**: Failed records automatically retry on next job run
2. **Observability**: Track every sync attempt with timestamps and errors
3. **Debugging**: Store failed payloads for investigation
4. **Auditing**: Complete history of all sync operations
5. **Recovery**: Manual retry endpoints for fixing issues
6. **Performance**: Don't re-process successfully synced records
