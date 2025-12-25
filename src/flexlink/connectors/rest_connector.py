"""Generic REST API connector with authentication and retry logic."""

import asyncio
import base64
import logging
from typing import Any

import httpx

from flexlink.core.connector import BaseConnector
from flexlink.models.connector import ConnectorConfig
from flexlink.models.request import IntegrationResponse

logger = logging.getLogger(__name__)


class RestConnector(BaseConnector):
    """
    Generic REST API connector supporting multiple authentication types and retry logic.

    Supports:
    - Authentication: basic, bearer, api_key, oauth2, none
    - Automatic retry with exponential backoff on 5xx errors and timeouts
    - Configurable timeout and retry attempts
    - Request/response transformation hooks
    """

    def __init__(self, config: ConnectorConfig, http_client: httpx.AsyncClient):
        """
        Initialize REST connector.

        Args:
            config: Connector configuration
            http_client: Shared async HTTP client instance
        """
        super().__init__(config)
        self.client = http_client

    async def send_request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> IntegrationResponse:
        """
        Send HTTP request to target system with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: Request path (will be appended to base_url)
            data: Request body data (for POST, PUT, PATCH)
            **kwargs: Additional request parameters (headers, params, etc.)
                params: Query string parameters (dict)
                headers: Request headers (dict)

        Returns:
            IntegrationResponse with status code, headers, body, and error (if any).
            - 4xx errors: returned immediately without retry
            - 5xx errors: retried with exponential backoff, then returned if all attempts fail
            - Timeouts: retried with exponential backoff

        Raises:
            httpx.TimeoutException: If all retry attempts timeout
            Exception: If request fails with non-HTTP error after all retry attempts

        Note:
            GET and DELETE requests will use query parameters (params) instead of
            JSON body, unless data is explicitly provided. This follows HTTP semantics.
        """
        # Build full URL
        url = f"{self.config.base_url}/{path.lstrip('/')}"

        # Merge headers: config defaults + auth headers + request-specific headers
        headers = {
            **self.config.headers,
            **self._get_auth_headers(),
            **kwargs.get("headers", {}),
        }

        # Extract query parameters from kwargs
        params = kwargs.get("params", {})

        # Remove headers and params from kwargs to avoid duplication
        kwargs = {k: v for k, v in kwargs.items() if k not in ("headers", "params")}

        # Determine request payload based on HTTP method
        # GET, DELETE, HEAD, OPTIONS should use query params, not body
        # Unless data is explicitly provided (some APIs support it)
        method_upper = method.upper()
        request_kwargs = {
            "method": method_upper,
            "url": url,
            "headers": headers,
            "timeout": self.config.timeout,
            **kwargs,
        }

        # For GET/DELETE/HEAD/OPTIONS: use params for query string, avoid body unless explicit
        if method_upper in ("GET", "DELETE", "HEAD", "OPTIONS"):
            if params:
                request_kwargs["params"] = params
            # Only include body if explicitly provided (non-empty)
            if data:
                request_kwargs["json"] = data
        else:
            # For POST/PUT/PATCH: use json body
            if data:
                request_kwargs["json"] = data
            # Also support query params for POST/PUT/PATCH if provided
            if params:
                request_kwargs["params"] = params

        # Retry loop with exponential backoff
        for attempt in range(self.config.retry_attempts):
            try:
                self.logger.debug(
                    f"Request attempt {attempt + 1}/{self.config.retry_attempts}: "
                    f"{method} {url} (params={params})"
                )

                response = await self.client.request(**request_kwargs)

                # Raise for 4xx and 5xx errors
                response.raise_for_status()

                # Success - parse and return response
                return IntegrationResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body=response.json() if response.content else None,
                )

            except httpx.HTTPStatusError as e:
                # CRITICAL: Don't retry 4xx client errors - return error response
                if 400 <= e.response.status_code < 500:
                    self.logger.error(
                        f"Client error {e.response.status_code} for {method} {url}: "
                        f"{e.response.text}"
                    )
                    # Return error response instead of raising
                    return IntegrationResponse(
                        status_code=e.response.status_code,
                        headers=dict(e.response.headers),
                        body=e.response.json() if e.response.content else None,
                        error=e.response.text or str(e),
                    )

                # Retry on 5xx server errors
                if attempt < self.config.retry_attempts - 1:
                    backoff = 2**attempt  # Exponential backoff: 1s, 2s, 4s, ...
                    self.logger.warning(
                        f"Server error {e.response.status_code} on {method} {url}. "
                        f"Retrying in {backoff}s... (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(backoff)
                else:
                    self.logger.error(
                        f"Server error {e.response.status_code} after "
                        f"{self.config.retry_attempts} attempts: {e.response.text}"
                    )
                    # Return error response instead of raising
                    return IntegrationResponse(
                        status_code=e.response.status_code,
                        headers=dict(e.response.headers),
                        body=e.response.json() if e.response.content else None,
                        error=e.response.text or str(e),
                    )

            except httpx.TimeoutException:
                if attempt < self.config.retry_attempts - 1:
                    backoff = 2**attempt
                    self.logger.warning(
                        f"Request timeout on {method} {url}. "
                        f"Retrying in {backoff}s... (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(backoff)
                else:
                    self.logger.error(
                        f"Request timeout after {self.config.retry_attempts} attempts"
                    )
                    raise

            except Exception as e:
                self.logger.error(f"Unexpected error on {method} {url}: {e}")
                raise

        # Should never reach here due to raise in loop
        raise RuntimeError("Retry loop exited unexpectedly")

    def _get_auth_headers(self) -> dict[str, str]:
        """
        Build authentication headers based on connector configuration.

        Returns:
            Dictionary of authentication headers

        Raises:
            ValueError: If authentication configuration is invalid
        """
        auth = self.config.auth
        auth_type = auth.type.lower()

        if auth_type == "none":
            return {}

        elif auth_type == "bearer":
            token = auth.credentials.get("token")
            if not token:
                raise ValueError("Bearer auth requires 'token' in credentials")
            return {"Authorization": f"Bearer {token}"}

        elif auth_type == "basic":
            username = auth.credentials.get("username")
            password = auth.credentials.get("password")
            if not username or not password:
                raise ValueError("Basic auth requires 'username' and 'password' in credentials")

            # Encode credentials in base64
            credentials = f"{username}:{password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}

        elif auth_type == "api_key":
            key = auth.credentials.get("key")
            header_name = auth.credentials.get("header", "X-API-Key")
            if not key:
                raise ValueError("API key auth requires 'key' in credentials")
            return {header_name: key}

        elif auth_type == "oauth2":
            # OAuth2 typically uses bearer token
            token = auth.credentials.get("access_token") or auth.credentials.get("token")
            if not token:
                raise ValueError("OAuth2 requires 'access_token' or 'token' in credentials")
            return {"Authorization": f"Bearer {token}"}

        else:
            raise ValueError(
                f"Unsupported auth type: {auth_type}. "
                f"Supported types: none, bearer, basic, api_key, oauth2"
            )

    async def transform_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform request data before sending (can be overridden by subclasses).

        Args:
            data: Original request data

        Returns:
            Transformed request data (default: no transformation)
        """
        return data

    async def transform_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform response data before returning (can be overridden by subclasses).

        Args:
            data: Original response data

        Returns:
            Transformed response data (default: no transformation)
        """
        return data
