"""Webhook output connector for HTTP POST notifications."""

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from flexlink.core.connector import BaseConnector
from flexlink.models.connector import ConnectorConfig
from flexlink.models.request import IntegrationResponse
from flexlink.models.webhook import WebhookConfig, WebhookDeliveryResult, WebhookAuthType

logger = logging.getLogger(__name__)


class WebhookConnector(BaseConnector):
    """
    Webhook connector for sending HTTP POST notifications.

    Features:
    - HTTP POST to configured webhook URL
    - HMAC-SHA256 signature generation
    - Multiple authentication methods (Bearer, API Key, Basic, HMAC)
    - Retry logic with exponential backoff
    - Statistics tracking
    """

    def __init__(
        self,
        config: ConnectorConfig,
        http_client: httpx.AsyncClient,
        webhook_config: WebhookConfig
    ):
        """
        Initialize webhook connector.

        Args:
            config: Base connector configuration
            http_client: Shared async HTTP client
            webhook_config: Webhook-specific configuration
        """
        super().__init__(config)
        self.http_client = http_client
        self.webhook_config = webhook_config

        # Statistics tracking
        self.total_deliveries = 0
        self.successful_deliveries = 0
        self.failed_deliveries = 0

    async def send_request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> IntegrationResponse:
        """
        Send data to webhook endpoint.

        Args:
            method: HTTP method (only POST supported for webhooks)
            path: Unused (webhook URL comes from config)
            data: Payload to send to webhook
            **kwargs: Additional parameters

        Returns:
            IntegrationResponse with delivery result
        """
        if method.upper() != "POST":
            return IntegrationResponse(
                status_code=405,
                error=f"Webhooks only support POST method, got {method}"
            )

        if not data:
            return IntegrationResponse(
                status_code=400,
                error="No data provided for webhook delivery"
            )

        # Deliver webhook with retry logic
        result = await self._deliver_webhook(data)

        # Convert to IntegrationResponse
        if result.success:
            return IntegrationResponse(
                status_code=result.status_code or 200,
                body={
                    "success": True,
                    "attempts": result.attempts,
                    "duration_ms": result.duration_ms,
                    "response": result.response_body
                }
            )
        else:
            return IntegrationResponse(
                status_code=result.status_code or 500,
                error=result.error,
                body={
                    "attempts": result.attempts,
                    "duration_ms": result.duration_ms
                }
            )

    async def _deliver_webhook(self, data: dict[str, Any]) -> WebhookDeliveryResult:
        """
        Deliver webhook with retry logic.

        Args:
            data: Payload to deliver

        Returns:
            WebhookDeliveryResult with delivery outcome
        """
        self.total_deliveries += 1
        start_time = time.time()

        attempts = 0
        last_error = None

        while attempts < self.webhook_config.max_retry_attempts:
            attempts += 1

            try:
                # Build headers
                headers = await self._build_headers(data)

                # Send POST request
                response = await self.http_client.post(
                    str(self.webhook_config.webhook_url),
                    json=data,
                    headers=headers,
                    timeout=self.webhook_config.timeout_seconds
                )

                duration_ms = (time.time() - start_time) * 1000

                # Success: 2xx status codes
                if 200 <= response.status_code < 300:
                    self.successful_deliveries += 1
                    logger.info(
                        f"Webhook delivered successfully: {self.webhook_config.webhook_url} "
                        f"(attempt {attempts}, {duration_ms:.2f}ms)"
                    )

                    # Parse response body if JSON
                    response_body = None
                    try:
                        response_body = response.json()
                    except Exception:
                        response_body = response.text

                    return WebhookDeliveryResult(
                        success=True,
                        status_code=response.status_code,
                        attempts=attempts,
                        duration_ms=duration_ms,
                        response_body=response_body
                    )

                # Client error (4xx): Don't retry
                elif 400 <= response.status_code < 500:
                    self.failed_deliveries += 1
                    error_msg = f"Webhook rejected (HTTP {response.status_code}): {response.text[:200]}"
                    logger.warning(error_msg)

                    return WebhookDeliveryResult(
                        success=False,
                        status_code=response.status_code,
                        attempts=attempts,
                        duration_ms=duration_ms,
                        error=error_msg
                    )

                # Server error (5xx): Retry
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(
                        f"Webhook delivery failed (attempt {attempts}/{self.webhook_config.max_retry_attempts}): "
                        f"{last_error}"
                    )

                    # Wait before retry (exponential backoff)
                    if attempts < self.webhook_config.max_retry_attempts:
                        delay = self.webhook_config.retry_backoff_factor ** (attempts - 1)
                        await self._sleep_with_jitter(delay)

            except httpx.TimeoutException as e:
                last_error = f"Timeout after {self.webhook_config.timeout_seconds}s"
                logger.warning(
                    f"Webhook timeout (attempt {attempts}/{self.webhook_config.max_retry_attempts}): "
                    f"{last_error}"
                )

                if attempts < self.webhook_config.max_retry_attempts:
                    delay = self.webhook_config.retry_backoff_factor ** (attempts - 1)
                    await self._sleep_with_jitter(delay)

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(
                    f"Webhook delivery error (attempt {attempts}/{self.webhook_config.max_retry_attempts}): "
                    f"{last_error}"
                )

                if attempts < self.webhook_config.max_retry_attempts:
                    delay = self.webhook_config.retry_backoff_factor ** (attempts - 1)
                    await self._sleep_with_jitter(delay)

        # All attempts failed
        self.failed_deliveries += 1
        duration_ms = (time.time() - start_time) * 1000

        return WebhookDeliveryResult(
            success=False,
            status_code=None,
            attempts=attempts,
            duration_ms=duration_ms,
            error=f"Failed after {attempts} attempts: {last_error}"
        )

    async def _build_headers(self, data: dict[str, Any]) -> dict[str, str]:
        """
        Build HTTP headers for webhook request.

        Args:
            data: Payload being sent

        Returns:
            Dictionary of headers
        """
        headers = {
            "Content-Type": "application/json",
            **self.webhook_config.custom_headers
        }

        # Add timestamp
        timestamp = str(int(time.time()))
        headers[self.webhook_config.timestamp_header] = timestamp

        # Add authentication
        if self.webhook_config.auth_type == WebhookAuthType.BEARER:
            token = self.webhook_config.auth_credentials.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif self.webhook_config.auth_type == WebhookAuthType.API_KEY:
            api_key = self.webhook_config.auth_credentials.get("api_key")
            header_name = self.webhook_config.auth_credentials.get("header_name", "X-API-Key")
            if api_key:
                headers[header_name] = api_key

        elif self.webhook_config.auth_type == WebhookAuthType.BASIC:
            username = self.webhook_config.auth_credentials.get("username", "")
            password = self.webhook_config.auth_credentials.get("password", "")
            import base64
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        # Add HMAC signature
        if self.webhook_config.signature_enabled and self.webhook_config.signature_secret:
            signature = self._generate_signature(data, timestamp)
            headers[self.webhook_config.signature_header] = signature

        return headers

    def _generate_signature(self, data: dict[str, Any], timestamp: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload.

        Args:
            data: Payload being sent
            timestamp: Unix timestamp string

        Returns:
            Hex-encoded HMAC signature
        """
        # Create deterministic payload: timestamp + JSON
        payload = f"{timestamp}.{json.dumps(data, sort_keys=True, separators=(',', ':'))}"

        # Generate HMAC-SHA256
        secret_key = self.webhook_config.signature_secret or ""
        secret = secret_key.encode('utf-8')
        message = payload.encode('utf-8')
        signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

        return signature

    async def _sleep_with_jitter(self, delay: float) -> None:
        """
        Sleep with jitter to avoid thundering herd.

        Args:
            delay: Base delay in seconds
        """
        import random
        import asyncio

        # Add ±20% jitter
        jitter = delay * 0.2 * (2 * random.random() - 1)
        actual_delay = max(0.1, delay + jitter)

        await asyncio.sleep(actual_delay)

    def get_stats(self) -> dict[str, Any]:
        """
        Get webhook connector statistics.

        Returns:
            Dictionary with delivery statistics
        """
        return {
            "total_deliveries": self.total_deliveries,
            "successful_deliveries": self.successful_deliveries,
            "failed_deliveries": self.failed_deliveries,
            "success_rate": (
                self.successful_deliveries / self.total_deliveries
                if self.total_deliveries > 0
                else 0.0
            ),
        }

    async def transform_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """No transformation by default."""
        return data

    async def transform_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """No transformation by default."""
        return data
