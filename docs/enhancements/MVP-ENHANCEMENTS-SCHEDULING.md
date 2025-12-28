# MVP Enhancement: Job Scheduling

## Overview
Add scheduled job execution to support periodic data synchronization (e.g., pull product changes every 30 minutes).

## Implementation Options

### Option 1: APScheduler (Recommended for MVP)
**Pros:**
- Lightweight, embedded in FastAPI app
- No external dependencies (Redis, broker)
- Simple cron-like syntax
- Good for MVP with single instance

**Cons:**
- Runs in-process (lost if app restarts)
- Not suitable for multi-instance without shared state

```python
# Add to pyproject.toml
dependencies = [
    "apscheduler>=3.10.0",
]

# src/flexlink/scheduler/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)

class JobScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Job scheduler started")

    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Job scheduler stopped")

    def add_job(self, func, cron_expression: str, job_id: str, **kwargs):
        """
        Add a scheduled job

        Args:
            func: Async function to execute
            cron_expression: Cron format (e.g., "*/30 * * * *" for every 30 min)
            job_id: Unique job identifier
            kwargs: Additional args passed to job function
        """
        self.scheduler.add_job(
            func,
            trigger=CronTrigger.from_crontab(cron_expression),
            id=job_id,
            replace_existing=True,
            kwargs=kwargs
        )
        logger.info(f"Scheduled job '{job_id}' with cron: {cron_expression}")

# src/flexlink/jobs/sync_jobs.py
import logging
from flexlink.core.registry import ConnectorRegistry
from flexlink.models.request import IntegrationRequest

logger = logging.getLogger(__name__)

async def sync_products_from_pim(registry: ConnectorRegistry):
    """
    Job: Pull product changes from iPIM Novomind every 30 minutes
    """
    logger.info("Starting product sync job from PIM")

    try:
        # Get PIM connector
        pim_connector = registry.get_connector("novomind_pim")
        shopware_connector = registry.get_connector("shopware6")

        # Pull changed products (last 30 min delta)
        # Assumes PIM API has a "changed_since" parameter
        request = IntegrationRequest(
            route="/api/products/delta",
            method="GET",
            query_params={"minutes": "30", "limit": "50"}
        )

        response = await pim_connector.send_request(
            method="GET",
            path="/api/products/delta",
            params={"minutes": "30", "limit": "50"}
        )

        if response.status_code == 200:
            products = response.body.get("products", [])
            logger.info(f"Fetched {len(products)} changed products from PIM")

            # Transform and push to Shopware
            for product in products:
                transformed = await transform_pim_to_shopware(product)
                await shopware_connector.send_request(
                    method="POST",
                    path="/api/product",
                    json=transformed
                )

            logger.info(f"Successfully synced {len(products)} products to Shopware")
        else:
            logger.error(f"PIM sync failed with status {response.status_code}")

    except Exception as e:
        logger.error(f"Product sync job failed: {str(e)}", exc_info=True)
        # Job will retry on next scheduled run

async def sync_orders_to_erp(registry: ConnectorRegistry):
    """
    Job: Pull new orders from Shopware and push to Business Central every 30 min
    """
    logger.info("Starting order sync job to ERP")

    try:
        shopware_connector = registry.get_connector("shopware6")
        bc_connector = registry.get_connector("business_central")

        # Get new orders from Shopware
        response = await shopware_connector.send_request(
            method="GET",
            path="/api/order",
            params={"filter[status]": "open", "limit": "100"}
        )

        if response.status_code == 200:
            orders = response.body.get("data", [])
            logger.info(f"Fetched {len(orders)} new orders from Shopware")

            # Push to Business Central
            for order in orders:
                transformed = await transform_shopware_to_bc(order)
                await bc_connector.send_request(
                    method="POST",
                    path="/api/v2.0/salesOrders",
                    json=transformed
                )

            logger.info(f"Successfully synced {len(orders)} orders to Business Central")
        else:
            logger.error(f"Order sync failed with status {response.status_code}")

    except Exception as e:
        logger.error(f"Order sync job failed: {str(e)}", exc_info=True)

# src/flexlink/main.py - Integration
from contextlib import asynccontextmanager
from fastapi import FastAPI
from flexlink.scheduler.scheduler import JobScheduler
from flexlink.jobs.sync_jobs import sync_products_from_pim, sync_orders_to_erp

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    http_client = httpx.AsyncClient(...)
    registry = ConnectorRegistry()
    await registry.load_connectors()

    # Start scheduler
    scheduler = JobScheduler()
    scheduler.add_job(
        func=sync_products_from_pim,
        cron_expression="*/30 * * * *",  # Every 30 minutes
        job_id="sync_products_pim",
        registry=registry
    )
    scheduler.add_job(
        func=sync_orders_to_erp,
        cron_expression="*/30 * * * *",  # Every 30 minutes
        job_id="sync_orders_erp",
        registry=registry
    )
    scheduler.start()

    app.state.http_client = http_client
    app.state.registry = registry
    app.state.scheduler = scheduler

    yield

    # Shutdown
    scheduler.shutdown()
    await http_client.aclose()
```

### Option 2: Celery + Redis/RabbitMQ (Phase 2)
Better for production multi-instance deployment, but overkill for MVP.

---

## Configuration

```yaml
# config/jobs.yaml
jobs:
  - id: sync_products_pim
    enabled: true
    cron: "*/30 * * * *"  # Every 30 minutes
    function: sync_products_from_pim
    max_instances: 1  # Prevent overlapping runs

  - id: sync_orders_erp
    enabled: true
    cron: "*/30 * * * *"
    function: sync_orders_to_erp
    max_instances: 1
```

---

## Testing

```python
# src/tests/test_scheduler/test_scheduler.py
import pytest
from flexlink.scheduler.scheduler import JobScheduler
import asyncio

@pytest.mark.asyncio
async def test_scheduler_adds_job():
    scheduler = JobScheduler()

    async def dummy_job():
        return "executed"

    scheduler.add_job(
        func=dummy_job,
        cron_expression="* * * * *",
        job_id="test_job"
    )

    jobs = scheduler.scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "test_job"

@pytest.mark.asyncio
async def test_sync_products_job_success(mock_registry, respx_mock):
    # Mock PIM API response
    respx_mock.get("https://pim.example.com/api/products/delta").mock(
        return_value=httpx.Response(
            200,
            json={"products": [{"id": "123", "name": "Test Product"}]}
        )
    )

    await sync_products_from_pim(mock_registry)
    # Assert product was pushed to Shopware
```

---

## Monitoring

Add endpoints to monitor job status:

```python
# src/flexlink/api/jobs.py
from fastapi import APIRouter, Depends, Request

jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])

@jobs_router.get("/status")
async def get_jobs_status(request: Request):
    """Get status of all scheduled jobs"""
    scheduler = request.app.state.scheduler
    jobs = scheduler.scheduler.get_jobs()

    return {
        "jobs": [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    }

@jobs_router.post("/trigger/{job_id}")
async def trigger_job_manually(job_id: str, request: Request):
    """Manually trigger a job (useful for testing)"""
    scheduler = request.app.state.scheduler
    job = scheduler.scheduler.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job.modify(next_run_time=datetime.now())
    return {"message": f"Job {job_id} triggered"}
```
