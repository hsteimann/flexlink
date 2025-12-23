"""Integration tests for error handling scenarios."""

import httpx
import pytest
import respx

from flexlink.connectors.file_connector import FileConnector
from flexlink.connectors.rest_connector import RestConnector
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.router import RequestRouter
from flexlink.core.transformation import TransformationEngine
from flexlink.models.connector import AuthConfig, ConnectorConfig
from flexlink.models.file import FileFormat
from flexlink.models.request import IntegrationRequest
from flexlink.models.transformation import RouteConfig, TransformationRule


@pytest.fixture
def http_client():
    """Create HTTP client."""
    return httpx.AsyncClient()


@pytest.mark.asyncio
@respx.mock
async def test_rest_connector_network_error(http_client):
    """Test REST connector handles network errors."""
    config = ConnectorConfig(
        name="test_api",
        type="rest",
        base_url="https://unreachable.test.com",
        auth=AuthConfig(type="none"),
    )
    connector = RestConnector(config, http_client)

    # Mock network error
    respx.get("https://unreachable.test.com/api/test").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    # Attempt request
    with pytest.raises(httpx.ConnectError):
        await connector.send_request("GET", "/api/test")


@pytest.mark.asyncio
@respx.mock
async def test_rest_connector_timeout_error(http_client):
    """Test REST connector handles timeout errors."""
    config = ConnectorConfig(
        name="slow_api",
        type="rest",
        base_url="https://slow.test.com",
        auth=AuthConfig(type="none"),
        timeout=1,  # 1 second timeout
    )
    connector = RestConnector(config, http_client)

    # Mock timeout
    respx.get("https://slow.test.com/api/slow").mock(side_effect=httpx.TimeoutException("Timeout"))

    # Attempt request
    with pytest.raises(httpx.TimeoutException):
        await connector.send_request("GET", "/api/slow")


@pytest.mark.asyncio
@respx.mock
async def test_rest_connector_server_error_retry(http_client):
    """Test REST connector retries on server errors."""
    config = ConnectorConfig(
        name="flaky_api",
        type="rest",
        base_url="https://flaky.test.com",
        auth=AuthConfig(type="none"),
        retry_attempts=3,
    )
    connector = RestConnector(config, http_client)

    # Mock server error
    route = respx.get("https://flaky.test.com/api/data").mock(
        return_value=httpx.Response(500, json={"error": "Internal Server Error"})
    )

    # Attempt request - should retry and eventually return error response
    response = await connector.send_request("GET", "/api/data")

    # Verify error response returned
    assert response.status_code == 500
    assert response.error is not None

    # Verify retries occurred (1 initial + 2 retries for 3 attempts total)
    assert route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_rest_connector_client_error_no_retry(http_client):
    """Test REST connector doesn't retry on client errors."""
    config = ConnectorConfig(
        name="strict_api",
        type="rest",
        base_url="https://strict.test.com",
        auth=AuthConfig(type="none"),
        retry_attempts=3,
    )
    connector = RestConnector(config, http_client)

    # Mock client error
    route = respx.post("https://strict.test.com/api/data").mock(
        return_value=httpx.Response(400, json={"error": "Bad Request"})
    )

    # Attempt request - should NOT retry, return error response
    response = await connector.send_request("POST", "/api/data", data={"invalid": "data"})

    # Verify error response returned without retry
    assert response.status_code == 400
    assert response.error is not None

    # Verify no retries (only 1 attempt)
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_file_connector_invalid_format():
    """Test file connector handles invalid file format gracefully."""
    config = ConnectorConfig(
        name="file",
        type="file",
        base_url="",
        auth=AuthConfig(type="none"),
    )
    connector = FileConnector(config)

    # Invalid JSON
    invalid_json = b"{ this is not valid json }"

    result = await connector.process_file(
        file_content=invalid_json, source_format=FileFormat.JSON
    )

    # Should return failure result
    assert result.success is False
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_file_connector_exceeds_size_limit():
    """Test file connector enforces size limit."""
    config = ConnectorConfig(
        name="file",
        type="file",
        base_url="",
        auth=AuthConfig(type="none"),
    )
    connector = FileConnector(config)

    # Create oversized file (>10MB)
    oversized_content = b"x" * (11 * 1024 * 1024)

    result = await connector.process_file(
        file_content=oversized_content, source_format=FileFormat.CSV
    )

    # Should return failure
    assert result.success is False
    assert any("File size" in error for error in result.errors)


@pytest.mark.asyncio
async def test_transformation_engine_invalid_transformation():
    """Test transformation engine handles unknown transformations."""
    data = {"value": "test"}
    rules = [
        TransformationRule(
            source_field="value",
            target_field="value",
            transformation="unknown_transform",
        )
    ]

    engine = TransformationEngine(rules)

    with pytest.raises(ValueError, match="Unknown transformation"):
        await engine.apply(data)


@pytest.mark.asyncio
async def test_transformation_engine_type_conversion_error():
    """Test transformation engine handles type conversion errors."""
    data = {"count": "not_a_number"}
    rules = [
        TransformationRule(
            source_field="count", target_field="count", transformation="int"
        )
    ]

    engine = TransformationEngine(rules)

    with pytest.raises(ValueError, match="Transformation failed"):
        await engine.apply(data)


@pytest.mark.asyncio
async def test_router_missing_connector():
    """Test router handles missing connector gracefully."""
    registry = ConnectorRegistry()
    router = RequestRouter(registry)

    # Add route to non-existent connector
    router.add_route(
        RouteConfig(
            path="/test",
            method="POST",
            connector="nonexistent",
            target_path="/api/test",
            transformations=[],
        )
    )

    request = IntegrationRequest(route="/test", method="POST", body={})

    response = await router.route_request(request)

    # Should return error response
    assert response.status_code == 500
    assert "Connector not found" in response.error


@pytest.mark.asyncio
async def test_router_no_matching_route():
    """Test router handles unmatched routes."""
    registry = ConnectorRegistry()
    router = RequestRouter(registry)

    request = IntegrationRequest(route="/unknown", method="GET")

    response = await router.route_request(request)

    # Should return 404
    assert response.status_code == 404
    assert "No route configured" in response.error


@pytest.mark.asyncio
async def test_router_method_mismatch():
    """Test router method matching."""
    registry = ConnectorRegistry()
    router = RequestRouter(registry)

    # Add POST route
    router.add_route(
        RouteConfig(
            path="/users",
            method="POST",
            connector="test",
            target_path="/api/users",
            transformations=[],
        )
    )

    # Try with GET
    request = IntegrationRequest(route="/users", method="GET")

    response = await router.route_request(request)

    # Should not match due to method mismatch
    assert response.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_router_transformation_failure(http_client):
    """Test router handles transformation failures."""
    registry = ConnectorRegistry()
    config = ConnectorConfig(
        name="test_api",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    connector = RestConnector(config, http_client)
    registry._connectors["test_api"] = connector

    router = RequestRouter(registry)

    # Add route with failing transformation
    router.add_route(
        RouteConfig(
            path="/convert",
            method="POST",
            connector="test_api",
            target_path="/api/convert",
            transformations=[
                TransformationRule(
                    source_field="age", target_field="age", transformation="int"
                )
            ],
        )
    )

    # Send request with invalid data
    request = IntegrationRequest(
        route="/convert", method="POST", body={"age": "invalid"}
    )

    response = await router.route_request(request)

    # Should return transformation error
    assert response.status_code == 400
    assert "transformation failed" in response.error.lower()


@pytest.mark.asyncio
async def test_registry_connector_not_found():
    """Test registry handles missing connector."""
    registry = ConnectorRegistry()

    with pytest.raises(KeyError):
        registry.get_connector("nonexistent")


@pytest.mark.asyncio
async def test_empty_file_processing():
    """Test handling of empty files."""
    config = ConnectorConfig(
        name="file",
        type="file",
        base_url="",
        auth=AuthConfig(type="none"),
    )
    connector = FileConnector(config)

    # Empty CSV
    empty_csv = b""

    result = await connector.process_file(
        file_content=empty_csv, source_format=FileFormat.CSV
    )

    # Should fail gracefully
    assert result.success is False
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_malformed_xml_processing():
    """Test handling of malformed XML."""
    config = ConnectorConfig(
        name="file",
        type="file",
        base_url="",
        auth=AuthConfig(type="none"),
    )
    connector = FileConnector(config)

    # Malformed XML
    malformed_xml = b"<data><row>missing closing tag"

    result = await connector.process_file(
        file_content=malformed_xml, source_format=FileFormat.XML
    )

    # Should fail gracefully
    assert result.success is False
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_file_conversion_with_incompatible_data():
    """Test file conversion with data that doesn't convert well."""
    config = ConnectorConfig(
        name="file",
        type="file",
        base_url="",
        auth=AuthConfig(type="none"),
    )
    connector = FileConnector(config)

    # CSV with inconsistent columns
    inconsistent_csv = b"id,name\n1,Alice\n2"  # Missing name in second row

    # Should still process but may have issues
    result = await connector.process_file(
        file_content=inconsistent_csv, source_format=FileFormat.CSV
    )

    # Pandas might handle this, so we just verify it doesn't crash
    assert result.records_processed >= 0
