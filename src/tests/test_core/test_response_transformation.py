"""
Response transformation tests for RequestRouter.

Tests cover:
- Dict response transformations
- List response transformations
- Nested field transformations
- Error handling (transformation failures)
- Empty transformation list (no-op)
- None response body (no transformation)
"""

import pytest
from flexlink.core.router import RequestRouter
from flexlink.core.registry import ConnectorRegistry
from flexlink.models.transformation import RouteConfig, TransformationRule
from flexlink.models.request import IntegrationRequest, IntegrationResponse
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_registry():
    """Mock connector registry with a test connector."""
    registry = MagicMock(spec=ConnectorRegistry)

    # Mock connector that returns predefined responses
    mock_connector = AsyncMock()
    registry.get_connector.return_value = mock_connector

    return registry, mock_connector


@pytest.mark.asyncio
async def test_response_transformation_dict_simple(mock_registry):
    """Test simple field mapping on dict response."""
    registry, mock_connector = mock_registry

    # Configure route with response transformation
    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        response_transformations=[
            TransformationRule(
                source_field="old_name",
                target_field="new_name"
            )
        ]
    )

    # Mock connector response
    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={"old_name": "John Doe", "age": 30}
    )

    # Execute request
    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/test", method="POST", body={})
    response = await router.route_request(request)

    # Verify transformation applied
    assert response.status_code == 200
    assert response.body["new_name"] == "John Doe"
    assert response.body["age"] == 30  # Untransformed field preserved


@pytest.mark.asyncio
async def test_response_transformation_list_of_dicts(mock_registry):
    """Test transformation on list of dict items."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        response_transformations=[
            TransformationRule(
                source_field="firstName",
                target_field="first_name"
            ),
            TransformationRule(
                source_field="lastName",
                target_field="last_name"
            )
        ]
    )

    # Mock list response
    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body=[
            {"firstName": "John", "lastName": "Doe"},
            {"firstName": "Jane", "lastName": "Smith"}
        ]
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/test", method="POST", body={})
    response = await router.route_request(request)

    # Verify all items transformed
    assert len(response.body) == 2
    assert response.body[0]["first_name"] == "John"
    assert response.body[0]["last_name"] == "Doe"
    assert response.body[1]["first_name"] == "Jane"
    assert response.body[1]["last_name"] == "Smith"


@pytest.mark.asyncio
async def test_response_transformation_nested_fields(mock_registry):
    """Test nested field access and creation."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        response_transformations=[
            TransformationRule(
                source_field="user.profile.name",
                target_field="userName"
            ),
            TransformationRule(
                source_field="metadata.createdAt",
                target_field="created"
            )
        ]
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={
            "user": {
                "profile": {"name": "John Doe", "age": 30}
            },
            "metadata": {"createdAt": "2024-01-01"}
        }
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/test", method="POST", body={})
    response = await router.route_request(request)

    # Verify nested transformation
    assert response.body["userName"] == "John Doe"
    assert response.body["created"] == "2024-01-01"


@pytest.mark.asyncio
async def test_response_transformation_with_value_transforms(mock_registry):
    """Test transformation functions (upper, lower, int, etc.)."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        response_transformations=[
            TransformationRule(
                source_field="name",
                target_field="name_upper",
                transformation="upper"
            ),
            TransformationRule(
                source_field="price",
                target_field="price_float",
                transformation="float"
            )
        ]
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={"name": "product", "price": "19.99"}
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/test", method="POST", body={})
    response = await router.route_request(request)

    # Verify transformations applied
    assert response.body["name_upper"] == "PRODUCT"
    assert response.body["price_float"] == 19.99
    assert isinstance(response.body["price_float"], float)


@pytest.mark.asyncio
async def test_response_transformation_empty_list(mock_registry):
    """Test that empty transformation list is no-op."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        response_transformations=[]  # Empty
    )

    original_body = {"name": "test", "value": 123}
    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body=original_body
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/test", method="POST", body={})
    response = await router.route_request(request)

    # Verify no transformation (original body unchanged)
    assert response.body == original_body


@pytest.mark.asyncio
async def test_response_transformation_none_body(mock_registry):
    """Test that None response body is handled gracefully."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        response_transformations=[
            TransformationRule(source_field="x", target_field="y")
        ]
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=204,
        body=None  # No content
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/test", method="POST", body={})
    response = await router.route_request(request)

    # Verify None body is preserved
    assert response.status_code == 204
    assert response.body is None


@pytest.mark.asyncio
async def test_response_transformation_error_handling(mock_registry):
    """Test that transformation errors don't break the response."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        response_transformations=[
            TransformationRule(
                source_field="nonexistent.field",  # Will fail
                target_field="result"
            )
        ]
    )

    original_body = {"data": "test"}
    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body=original_body
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/test", method="POST", body={})
    response = await router.route_request(request)

    # Verify original response returned on transformation error
    assert response.status_code == 200
    # Response should be original (transformation failed gracefully)
    assert response.body == original_body


@pytest.mark.asyncio
async def test_response_transformation_priceedge_example(mock_registry):
    """Real-world example: PriceEdge response transformation."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/pricing/suggested-prices",
        connector="priceedge",
        target_path="/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price",
        response_transformations=[
            TransformationRule(
                source_field="Data.data",
                target_field="items"
            )
        ]
    )

    # Mock PriceEdge response format
    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={
            "Data": {
                "data": [
                    {"cd_ItemNumber": "ITEM001", "Value": 19.99},
                    {"cd_ItemNumber": "ITEM002", "Value": 29.99}
                ],
                "total": 2
            }
        }
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/pricing/suggested-prices", method="POST", body={})
    response = await router.route_request(request)

    # Verify transformation
    assert "items" in response.body
    assert len(response.body["items"]) == 2
    assert response.body["items"][0]["cd_ItemNumber"] == "ITEM001"
