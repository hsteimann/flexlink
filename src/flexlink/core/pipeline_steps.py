"""Pipeline step implementations."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from flexlink.core.connector import BaseConnector
from flexlink.core.pipeline_context import PipelineRunContext

logger = logging.getLogger(__name__)


# Custom exceptions
class ExtractError(Exception):
    """Raised when extraction fails."""
    pass


class TransformError(Exception):
    """Raised when transformation fails."""
    pass


class LoadError(Exception):
    """Raised when loading fails."""
    pass


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class PipelineStep(ABC):
    """Base class for all pipeline steps."""

    @abstractmethod
    async def execute(self, context: PipelineRunContext) -> None:
        """
        Execute step logic and update context.

        Args:
            context: Shared execution context (mutated in-place)
        """
        pass


class ExtractStep(PipelineStep):
    """
    Extract data from source connector with pagination support.

    Supports multiple pagination strategies:
    - offset/limit: Traditional offset-based pagination (?offset=0&limit=100)
    - cursor: Cursor/token-based pagination (?cursor=abc123)
    - page: Page number-based pagination (?page=1&page_size=100)
    """

    def __init__(
        self,
        connector: BaseConnector,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        pagination: dict[str, Any] | None = None
    ):
        self.connector = connector
        self.method = method
        self.path = path
        self.params = params or {}
        self.pagination_config = pagination or {}

    async def execute(self, context: PipelineRunContext) -> None:
        """
        Fetch data from connector with optional pagination.

        Handles automatic page iteration and record accumulation.

        Args:
            context: Pipeline run context (mutated in-place)
        """
        # Check if pagination is enabled
        if self.pagination_config.get("enabled", False):
            records = await self._extract_with_pagination(context)
        else:
            records = await self._extract_single_request()

        # Update context (mutation)
        context.data = records
        context.metadata.records_extracted = len(records)

        logger.info(
            f"Extracted {len(records)} records from {self.connector.config.name}",
            extra={
                "run_id": context.run_id,
                "connector": self.connector.config.name,
                "record_count": len(records)
            }
        )

    async def _extract_single_request(self) -> list[dict]:
        """Extract data from a single request without pagination."""
        response = await self.connector.send_request(
            method=self.method,
            path=self.path,
            data=self.params.get("body"),
            params=self.params.get("query_params")
        )

        if response.status_code >= 400:
            raise ExtractError(
                f"Extract failed: HTTP {response.status_code} - {response.error}"
            )

        return self._extract_records(response.body)

    async def _extract_with_pagination(self, context: PipelineRunContext) -> list[dict]:
        """
        Extract data with pagination support.

        Supports:
        - offset/limit: ?offset=0&limit=100
        - cursor: ?cursor=abc123
        - page: ?page=1&page_size=100
        """
        strategy = self.pagination_config.get("strategy", "offset")
        max_pages = self.pagination_config.get("max_pages", 100)
        page_size = self.pagination_config.get("page_size", 100)

        if strategy == "offset":
            all_records = await self._paginate_offset(page_size, max_pages, context)
        elif strategy == "cursor":
            all_records = await self._paginate_cursor(page_size, max_pages, context)
        elif strategy == "page":
            all_records = await self._paginate_page(page_size, max_pages, context)
        else:
            raise ValueError(f"Unknown pagination strategy: {strategy}")

        return all_records

    async def _paginate_offset(
        self,
        page_size: int,
        max_pages: int,
        context: PipelineRunContext
    ) -> list[dict]:
        """Paginate using offset/limit strategy."""
        all_records = []
        offset = 0

        for page in range(max_pages):
            query_params = self.params.get("query_params", {}).copy()
            query_params["offset"] = offset
            query_params["limit"] = page_size

            response = await self.connector.send_request(
                method=self.method,
                path=self.path,
                data=self.params.get("body"),
                params=query_params
            )

            if response.status_code >= 400:
                raise ExtractError(
                    f"Extract failed on page {page + 1}: HTTP {response.status_code}"
                )

            records = self._extract_records(response.body)
            all_records.extend(records)

            logger.debug(f"Fetched page {page + 1}: {len(records)} records")

            if len(records) < page_size:
                break

            offset += page_size

        return all_records

    async def _paginate_cursor(
        self,
        page_size: int,
        max_pages: int,
        context: PipelineRunContext
    ) -> list[dict]:
        """Paginate using cursor/token strategy."""
        all_records = []
        cursor = None
        cursor_param = self.pagination_config.get("cursor_param", "cursor")
        next_cursor_path = self.pagination_config.get("next_cursor_path", "pagination.next_cursor")

        for page in range(max_pages):
            query_params = self.params.get("query_params", {}).copy()

            if cursor:
                query_params[cursor_param] = cursor

            size_param = self.pagination_config.get("size_param", "limit")
            query_params[size_param] = page_size

            response = await self.connector.send_request(
                method=self.method,
                path=self.path,
                data=self.params.get("body"),
                params=query_params
            )

            if response.status_code >= 400:
                raise ExtractError(
                    f"Extract failed on page {page + 1}: HTTP {response.status_code}"
                )

            records = self._extract_records(response.body)
            all_records.extend(records)

            logger.debug(f"Fetched page {page + 1}: {len(records)} records")

            cursor = self._get_nested_value(response.body, next_cursor_path)

            if not cursor or len(records) == 0:
                break

        return all_records

    async def _paginate_page(
        self,
        page_size: int,
        max_pages: int,
        context: PipelineRunContext
    ) -> list[dict]:
        """Paginate using page number strategy."""
        all_records = []
        page_param = self.pagination_config.get("page_param", "page")
        size_param = self.pagination_config.get("size_param", "page_size")
        start_page = self.pagination_config.get("start_page", 1)

        for page_num in range(start_page, start_page + max_pages):
            query_params = self.params.get("query_params", {}).copy()
            query_params[page_param] = page_num
            query_params[size_param] = page_size

            response = await self.connector.send_request(
                method=self.method,
                path=self.path,
                data=self.params.get("body"),
                params=query_params
            )

            if response.status_code >= 400:
                raise ExtractError(
                    f"Extract failed on page {page_num}: HTTP {response.status_code}"
                )

            records = self._extract_records(response.body)
            all_records.extend(records)

            logger.debug(f"Fetched page {page_num}: {len(records)} records")

            if len(records) < page_size:
                break

        return all_records

    def _extract_records(self, response_body: dict | list | None) -> list[dict]:
        """
        Extract records from response body.

        Handles common API response patterns:
        - Direct list: [{"id": 1}, {"id": 2}]
        - Nested list: {"data": [{"id": 1}], "meta": {}}
        - Single object: {"id": 1, "name": "test"}
        - None/empty responses: []
        """
        if response_body is None:
            return []

        if isinstance(response_body, list):
            return response_body

        if isinstance(response_body, dict):
            data_path = self.pagination_config.get("data_path", None)

            if data_path:
                records = self._get_nested_value(response_body, data_path)
                if isinstance(records, list):
                    return records
            else:
                for key in ["data", "items", "records", "results", "rows"]:
                    if key in response_body and isinstance(response_body[key], list):
                        return response_body[key]

            return [response_body]

        return []

    def _get_nested_value(self, data: Any, path: str) -> Any:
        """
        Get nested value from dict using dot notation.

        Example: "pagination.next_cursor" -> data["pagination"]["next_cursor"]

        Args:
            data: Data to extract from (should be dict, but handles other types gracefully)
            path: Dot-notation path to nested value

        Returns:
            Nested value if found, None otherwise
        """
        if not path or not isinstance(data, dict):
            return None

        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value


class TransformStep(PipelineStep):
    """Transform data using mapping configuration."""

    def __init__(
        self,
        transformation_engine,  # TransformationEngine
        validator,  # Validator | None
        mapping  # MappingConfig
    ):
        self.transformation_engine = transformation_engine
        self.validator = validator
        self.mapping = mapping

    async def execute(self, context: PipelineRunContext) -> None:
        """
        Apply transformation to each record in context.

        Args:
            context: Pipeline run context (mutated in-place)
        """
        if not context.data:
            logger.warning("No data to transform")
            return

        transformed = []
        validation_errors = []

        for i, record in enumerate(context.data):
            try:
                # Apply transformation
                result = await self.transformation_engine.apply(record)

                # Apply validation if configured
                if self.validator:
                    validation_result = await self.validator.validate(result)

                    if not validation_result.valid:
                        # Handle based on strategy
                        if self.mapping.validation.on_validation_error == "skip_row":
                            logger.warning(f"Skipping invalid record {i}: {validation_result.errors}")
                            validation_errors.extend(validation_result.errors)
                            continue
                        elif self.mapping.validation.on_validation_error == "fail_pipeline":
                            raise ValidationError(
                                f"Validation failed for record {i}: {validation_result.errors}"
                            )

                transformed.append(result)

            except ValidationError:
                # Re-raise ValidationError without wrapping
                raise
            except Exception as e:
                logger.error(f"Error transforming record {i}: {e}")
                raise TransformError(f"Transformation failed: {e}")

        # Update context (mutation)
        context.data = transformed
        context.metadata.records_transformed = len(transformed)
        context.metadata.validation_errors = len(validation_errors)

        logger.info(
            f"Transformed {len(transformed)} records "
            f"({len(validation_errors)} validation errors)"
        )


class LoadStep(PipelineStep):
    """
    Load data to output connector with batch support.

    Supports two loading strategies:
    - per_record: Send each record individually (default)
    - batch: Send records in batches for efficiency
    """

    def __init__(
        self,
        connector: BaseConnector,
        operation: str | None = None,
        params: dict[str, Any] | None = None,
        batch_config: dict[str, Any] | None = None
    ):
        self.connector = connector
        self.operation = operation or "insert"
        self.params = params or {}
        self.batch_config = batch_config or {}

    async def execute(self, context: PipelineRunContext) -> None:
        """
        Send data to output connector.

        Args:
            context: Pipeline run context (mutated in-place)
        """
        if not context.data:
            logger.warning("No data to load")
            return

        batch_enabled = self.batch_config.get("enabled", False)

        if batch_enabled:
            success_count, error_count = await self._load_batch(context.data, context)
        else:
            success_count, error_count = await self._load_per_record(context.data, context)

        # Update context (mutation)
        context.metadata.records_loaded = success_count

        logger.info(
            f"Loaded {success_count} records to {self.connector.config.name} "
            f"({error_count} errors)",
            extra={
                "run_id": context.run_id,
                "connector": self.connector.config.name,
                "success_count": success_count,
                "error_count": error_count,
                "mode": "batch" if batch_enabled else "per_record"
            }
        )

        if error_count > 0 and success_count == 0:
            raise LoadError(f"All records failed to load ({error_count} errors)")

    async def _load_per_record(
        self,
        records: list[dict],
        context: PipelineRunContext
    ) -> tuple[int, int]:
        """Load records one at a time."""
        success_count = 0
        error_count = 0

        for i, record in enumerate(records):
            try:
                response = await self.connector.send_request(
                    method=self.params.get("method", "POST"),
                    path=self.params.get("path", ""),
                    data=record,
                    params=self.params.get("query_params")
                )

                if response.status_code >= 400:
                    logger.error(
                        f"Load failed for record {i}: HTTP {response.status_code} - {response.error}"
                    )
                    error_count += 1
                else:
                    success_count += 1

            except Exception as e:
                logger.error(f"Error loading record {i}: {e}")
                error_count += 1

        return success_count, error_count

    async def _load_batch(
        self,
        records: list[dict],
        context: PipelineRunContext
    ) -> tuple[int, int]:
        """Load records in batches for efficiency."""
        batch_size = self.batch_config.get("batch_size", 100)
        batch_wrapper = self.batch_config.get("wrapper_key", None)
        success_count = 0
        error_count = 0

        batches = [
            records[i:i + batch_size]
            for i in range(0, len(records), batch_size)
        ]

        logger.debug(f"Loading {len(records)} records in {len(batches)} batches")

        for batch_num, batch in enumerate(batches):
            try:
                if batch_wrapper:
                    payload = {batch_wrapper: batch}
                else:
                    payload = batch

                response = await self.connector.send_request(
                    method=self.params.get("method", "POST"),
                    path=self.params.get("path", ""),
                    data=payload,
                    params=self.params.get("query_params")
                )

                if response.status_code >= 400:
                    logger.error(
                        f"Batch {batch_num + 1} failed: HTTP {response.status_code} - {response.error}"
                    )
                    error_count += len(batch)
                else:
                    partial_errors = self._check_partial_failures(response.body, batch)

                    if partial_errors:
                        success_count += len(batch) - partial_errors
                        error_count += partial_errors
                        logger.warning(
                            f"Batch {batch_num + 1}: {partial_errors}/{len(batch)} records failed"
                        )
                    else:
                        success_count += len(batch)
                        logger.debug(f"Batch {batch_num + 1}: {len(batch)} records loaded")

            except Exception as e:
                logger.error(f"Error loading batch {batch_num + 1}: {e}")
                error_count += len(batch)

        return success_count, error_count

    def _check_partial_failures(
        self,
        response_body: dict | list | None,
        batch: list[dict]
    ) -> int:
        """Check response for partial failures."""
        if response_body is None or not isinstance(response_body, dict):
            return 0

        results = None
        for key in ["results", "items", "records", "data"]:
            if key in response_body and isinstance(response_body[key], list):
                results = response_body[key]
                break

        if not results or len(results) != len(batch):
            return 0

        error_count = 0
        status_field = self.batch_config.get("status_field", "status")
        success_values = self.batch_config.get("success_values", ["success", "ok", "created"])

        for result in results:
            if isinstance(result, dict):
                status = result.get(status_field)
                if status and status.lower() not in success_values:
                    error_count += 1

        return error_count
