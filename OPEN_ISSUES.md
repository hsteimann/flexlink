# Open Architectural Issues

This document tracks identified architectural improvements that should be addressed in future releases.

## Performance & Scalability

### Issue #1: Blocking Filesystem I/O in Async Routes

**Status:** Open
**Priority:** Medium
**Affects:** `src/flexlink/api/files.py` (lines 95-118, 256-288)
**Reported:** December 2024

**Description:**

File upload and cleanup endpoints use synchronous filesystem calls directly inside async route handlers:
- `file_path.write_bytes()` - Blocking write during file upload
- `iterdir()`, `unlink()` - Blocking operations during cleanup
- These operations run on the event loop thread

**Impact:**

Even with the 10 MB file size cap, blocking I/O operations delay all other concurrent requests while files are being written or purged. This violates the async middleware's non-blocking guarantees and can cause request latency spikes under load.

**Proposed Solutions:**

1. **Thread Pool Offloading:**
   ```python
   # Option A: asyncio.to_thread (Python 3.9+)
   await asyncio.to_thread(file_path.write_bytes, content)

   # Option B: Starlette's run_in_threadpool
   from starlette.concurrency import run_in_threadpool
   await run_in_threadpool(file_path.write_bytes, content)
   ```

2. **Async Filesystem Library:**
   - Use `aiofiles` for async file operations
   - Example: `async with aiofiles.open(file_path, 'wb') as f: await f.write(content)`

3. **Background Task Queue:**
   - Offload file writes to background tasks
   - Return immediately with 202 Accepted status
   - Poll for completion via separate endpoint

**Files to Modify:**
- `src/flexlink/api/files.py:95-118` (upload endpoint file persistence)
- `src/flexlink/api/files.py:256-288` (cleanup endpoint file deletion)

**Acceptance Criteria:**
- [ ] No blocking filesystem calls in async route handlers
- [ ] File I/O offloaded to thread pool or async library
- [ ] Performance benchmarks show improved concurrency under load
- [ ] All existing tests pass
- [ ] New tests verify async behavior

---

### Issue #2: Sequential Record Forwarding in File-to-REST Pipeline

**Status:** Open
**Priority:** Medium
**Affects:** `src/flexlink/api/files.py` (lines 342-417)
**Reported:** December 2024

**Description:**

The `/api/v1/files/forward` endpoint forwards records sequentially in the request context:
- Individual mode: Hundreds of sequential `await route_request()` calls in a single HTTP request
- Client connection remains open for the entire batch
- FastAPI worker is busy for the entire file-processing duration
- Any slow downstream connector stalls the whole ingestion

**Impact:**

Large CSV files with thousands of records can tie up a worker for minutes:
- 1000 records × 500ms per API call = 8+ minutes of blocking
- Client timeouts on large batches
- Worker starvation under concurrent file uploads
- No progress visibility during long-running operations

**Example Scenario:**
```
Upload 5,000 record CSV → Forward to slow external API (200ms/record)
= 1,000 seconds (16+ minutes) with connection held open
```

**Proposed Solutions:**

1. **Background Task Queue (Recommended):**
   ```python
   # Return immediately with task ID
   task_id = await queue.enqueue(forward_records, records, route)
   return {"task_id": task_id, "status": "processing"}

   # Poll for status
   GET /api/v1/files/forward/status/{task_id}
   ```

2. **Concurrent Batching:**
   ```python
   # Process N records concurrently
   async with asyncio.TaskGroup() as tg:
       for batch in chunks(records, size=50):
           tg.create_task(forward_batch(batch))
   ```

3. **Streaming Response:**
   ```python
   # Stream results as records are processed
   async def stream_results():
       for record in records:
           result = await route_request(record)
           yield json.dumps(result) + "\n"

   return StreamingResponse(stream_results())
   ```

4. **Hybrid Approach:**
   - Small files (<100 records): Process synchronously
   - Large files (≥100 records): Background task with status polling
   - Add `async_mode` parameter for client control

**Files to Modify:**
- `src/flexlink/api/files.py:342-417` (forward endpoint)
- Consider new `src/flexlink/tasks/` module for background processing
- Add task status tracking (Redis, database, or in-memory for MVP)

**Acceptance Criteria:**
- [ ] Large file uploads don't block workers for extended periods
- [ ] Progress visibility for long-running operations
- [ ] Configurable concurrency limits
- [ ] Graceful handling of slow/failed downstream APIs
- [ ] Client can poll for completion status
- [ ] All existing tests pass
- [ ] New tests for async/background processing

**Additional Considerations:**
- Task queue library: Celery, Dramatiq, or simple asyncio.Queue
- Progress tracking: WebSocket updates or SSE for real-time status
- Error handling: Partial success scenarios (500/1000 records forwarded)
- Retry logic: Failed records can be retried independently

---

## Priority Ordering

Based on impact and complexity:

1. **Issue #2** (File-to-REST Sequential Processing) - Higher impact on production scalability
2. **Issue #1** (Blocking Filesystem I/O) - Lower impact due to 10MB cap, but easier to fix

---

## Implementation Notes

Both issues are architectural improvements that don't break existing functionality. They can be addressed incrementally:

**Phase 1:** Issue #1 (Async File I/O)
- Lower complexity, smaller code change
- Immediate benefit for concurrent uploads
- Good warmup for Phase 2

**Phase 2:** Issue #2 (Background Task Queue)
- Requires more infrastructure (task queue)
- Larger architectural change
- Enables future features (bulk operations, scheduled tasks)

**Testing Strategy:**
- Load tests with concurrent file uploads
- Large file forwarding benchmarks (1000+ records)
- Verify no regressions in existing functionality
- Monitor worker utilization and request latency
