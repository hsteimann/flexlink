"""PriceEdge API specialized connector."""

import logging
from typing import Any

import httpx

from flexlink.connectors.rest_connector import RestConnector
from flexlink.models.connector import ConnectorConfig
from flexlink.models.request import IntegrationResponse

logger = logging.getLogger(__name__)


class PriceEdgeConnector(RestConnector):
    """
    Specialized connector for PriceEdge pricing platform.

    PriceEdge API Characteristics:
    - Pagination: POST requests with page/nrOfRecords in body
    - Auth: Custom "ApiKey {key_name}:{token}" header format
    - Responses: Wrapped in Data.data structure
    - Endpoints: Table-based API structure

    Documentation: https://priceedge.mintlify.app/
    """

    def __init__(self, config: ConnectorConfig, http_client: httpx.AsyncClient):
        """Initialize PriceEdge connector with custom settings."""
        super().__init__(config, http_client)
        self.logger.info("Initialized PriceEdge specialized connector")

    async def send_request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> IntegrationResponse:
        """
        Send HTTP request and apply PriceEdge response transformation.

        Overrides base method to automatically unwrap Data.data structure.
        """
        response = await super().send_request(method, path, data, **kwargs)

        # Apply transformation if response has body
        if response.body is not None:
            transformed_body = await self.transform_response(response.body)
            # Create new response with transformed body
            response = IntegrationResponse(
                status_code=response.status_code,
                headers=response.headers,
                body=transformed_body,
                error=response.error
            )

        return response

    async def query_suggested_prices(
        self,
        item_ids: list[str],
        page_size: int = 100,
        max_pages: int = 100
    ) -> list[dict[str, Any]]:
        """
        Query suggested prices for items with automatic pagination.

        Args:
            item_ids: List of item identifiers (cd_ItemNumber)
            page_size: Records per page (default: 100)
            max_pages: Maximum pages to fetch (safety limit)

        Returns:
            List of price records (Data.data unwrapped)
        """
        all_records = []
        page = 1

        filters = [{
            "columnName": "cd_ItemNumber",
            "op": "containsAny",
            "value": ",".join(item_ids)
        }]

        while page <= max_pages:
            response = await self._fetch_page(
                table="Item_PriceList_SuggestedPrices_Suggested_Price",
                page=page,
                page_size=page_size,
                filters=filters
            )

            records = response.body
            # Handle both list and dict returns (unwrapped vs not unwrapped)
            if isinstance(records, list):
                if not records:
                    break
                all_records.extend(records)
            else:
                # Shouldn't happen but handle gracefully
                break

            self.logger.debug(
                f"PriceEdge: Fetched page {page}, {len(records)} records "
                f"(total: {len(all_records)})"
            )

            if len(records) < page_size:
                break  # Last page

            page += 1

        return all_records

    async def _fetch_page(
        self,
        table: str,
        page: int,
        page_size: int,
        filters: list[dict[str, Any]]
    ) -> IntegrationResponse:
        """
        Fetch a single page from PriceEdge table.

        Uses PriceEdge-specific body-based pagination.
        """
        body = {
            "page": page,
            "nrOfRecords": page_size,
            "filters": filters
        }

        path = f"api/tables/{table}"

        return await self.send_request(
            method="POST",
            path=path,
            data=body
        )

    async def transform_response(self, data: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
        """
        Unwrap PriceEdge's Data.data response structure.

        PriceEdge wraps responses like:
        {
            "Data": {
                "data": [...],
                "totalRecords": 500,
                "page": 1
            }
        }

        Extract just the data array.
        """
        if isinstance(data, dict) and "Data" in data:
            if "data" in data["Data"]:
                return data["Data"]["data"]

        # If not wrapped, return as-is
        return data
