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

from unittest.mock import AsyncMock, MagicMock

import pytest

from flexlink.core.registry import ConnectorRegistry
from flexlink.core.router import RequestRouter
from flexlink.models.request import IntegrationRequest, IntegrationResponse
from flexlink.models.transformation import RouteConfig, TransformationRule


@pytest.fixture
def mock_registry():
    """Mock connector registry with a test connector."""
    registry = MagicMock(spec=ConnectorRegistry)

    # Mock connector that returns predefined responses
    mock_connector = AsyncMock()

    # Configure transform methods to return data unchanged (identity function)
    async def identity_transform(data):
        return data

    mock_connector.transform_request = AsyncMock(side_effect=identity_transform)
    mock_connector.transform_response = AsyncMock(side_effect=identity_transform)

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

@pytest.mark.asyncio
async def test_response_filtering_with_include_fields(mock_registry):
    """Test response transformation with include_fields."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/api/users",
        connector="test",
        target_path="/users",
        response_transformations=[
            TransformationRule(
                source_field="name",
                target_field="name",
                include_fields=["id", "name", "email"]
            )
        ]
    )

    # Mock response with extra fields
    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "password": "hashed_password",
            "internal_id": 12345
        }
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/api/users", method="POST", body={})
    response = await router.route_request(request)

    assert response.status_code == 200
    assert response.body == {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com"
    }
    assert "password" not in response.body
    assert "internal_id" not in response.body


@pytest.mark.asyncio
async def test_response_filtering_with_exclude_fields(mock_registry):
    """Test response transformation with exclude_fields."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/api/users",
        connector="test",
        target_path="/users",
        response_transformations=[
            TransformationRule(
                source_field="name",
                target_field="name",
                exclude_fields=["password", "internal_id", "ssn"]
            )
        ]
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "password": "hashed_password",
            "internal_id": 12345,
            "ssn": "123-45-6789"
        }
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/api/users", method="POST", body={})
    response = await router.route_request(request)

    assert response.status_code == 200
    assert response.body["id"] == 1
    assert response.body["name"] == "John Doe"
    assert response.body["email"] == "john@example.com"
    assert "password" not in response.body
    assert "internal_id" not in response.body
    assert "ssn" not in response.body


@pytest.mark.asyncio
async def test_response_filtering_list_responses(mock_registry):
    """Test filtering works with list responses."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/api/users",
        connector="test",
        target_path="/users",
        response_transformations=[
            TransformationRule(
                source_field="name",
                target_field="name",
                exclude_fields=["password"]
            )
        ]
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body=[
            {"id": 1, "name": "John", "password": "hash1"},
            {"id": 2, "name": "Jane", "password": "hash2"}
        ]
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/api/users", method="POST", body={})
    response = await router.route_request(request)

    assert response.status_code == 200
    assert len(response.body) == 2
    for user in response.body:
        assert "password" not in user
        assert "id" in user
        assert "name" in user


@pytest.mark.asyncio
async def test_response_filtering_nested_fields(mock_registry):
    """Test filtering with nested field paths."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/api/users",
        connector="test",
        target_path="/users",
        response_transformations=[
            TransformationRule(
                source_field="user.name",
                target_field="user.name",
                exclude_fields=["user.password", "user.internal_notes"]
            )
        ]
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={
            "user": {
                "name": "John Doe",
                "email": "john@example.com",
                "password": "secret",
                "internal_notes": "VIP customer"
            }
        }
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/api/users", method="POST", body={})
    response = await router.route_request(request)

    assert response.status_code == 200
    assert response.body["user"]["name"] == "John Doe"
    assert response.body["user"]["email"] == "john@example.com"
    assert "password" not in response.body["user"]
    assert "internal_notes" not in response.body["user"]


@pytest.mark.asyncio
async def test_response_filtering_with_transformation(mock_registry):
    """Test filtering combined with field transformation."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/api/products",
        connector="test",
        target_path="/products",
        response_transformations=[
            TransformationRule(
                source_field="internal_code",
                target_field="product_code",
                transformation="upper",
                exclude_fields=["internal_code", "cost_price"]
            )
        ]
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={
            "internal_code": "abc123",
            "name": "Widget",
            "cost_price": 5.99,
            "sale_price": 9.99
        }
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/api/products", method="POST", body={})
    response = await router.route_request(request)

    assert response.status_code == 200
    assert response.body["product_code"] == "ABC123"  # Transformed
    assert response.body["name"] == "Widget"
    assert response.body["sale_price"] == 9.99
    assert "internal_code" not in response.body  # Excluded
    assert "cost_price" not in response.body  # Excluded


@pytest.mark.asyncio
async def test_response_transformation_with_jsonata_expression(mock_registry):
    """Test response transformation using JSONata expression."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/api/users",
        connector="test",
        target_path="/users",
        response_transformations=[
            TransformationRule(
                source_field="user",  # Ignored
                target_field="fullName",
                expression='$uppercase(firstName & " " & lastName)',
            )
        ],
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={"firstName": "john", "lastName": "doe", "email": "john@example.com"},
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/api/users", method="POST", body={})
    response = await router.route_request(request)

    assert response.status_code == 200
    assert response.body["fullName"] == "JOHN DOE"
    assert response.body["firstName"] == "john"  # Original preserved


@pytest.mark.asyncio
async def test_response_transformation_jsonata_array_aggregation(mock_registry):
    """Test JSONata array aggregation in response."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/api/orders",
        connector="test",
        target_path="/orders",
        response_transformations=[
            TransformationRule(
                source_field="items",
                target_field="totalAmount",
                expression="$sum(items.amount)",
            ),
            TransformationRule(
                source_field="items",
                target_field="itemCount",
                expression="$count(items)",
            ),
        ],
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200, body={"items": [{"amount": 100}, {"amount": 200}, {"amount": 150}]}
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/api/orders", method="POST", body={})
    response = await router.route_request(request)

    assert response.status_code == 200
    assert response.body["totalAmount"] == 450
    assert response.body["itemCount"] == 3


@pytest.mark.asyncio
async def test_response_transformation_jsonata_with_filtering(mock_registry):
    """Test JSONata combined with field filtering."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/api/products",
        connector="test",
        target_path="/products",
        response_transformations=[
            TransformationRule(
                source_field="product",
                target_field="summary",
                expression='{"name": $uppercase(name), "price": price}',
                exclude_fields=["internal_id", "cost"],
            )
        ],
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={"name": "widget", "price": 99.99, "internal_id": 12345, "cost": 50.00},
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/api/products", method="POST", body={})
    response = await router.route_request(request)

    assert response.status_code == 200
    assert response.body["summary"]["name"] == "WIDGET"
    assert response.body["summary"]["price"] == 99.99
    assert "internal_id" not in response.body
    assert "cost" not in response.body


@pytest.mark.asyncio
async def test_response_transformation_jsonata_list_response(mock_registry):
    """Test JSONata on list responses."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/api/users",
        connector="test",
        target_path="/users",
        response_transformations=[
            TransformationRule(
                source_field="firstName",  # Applied to each item
                target_field="fullName",
                expression='$uppercase(firstName & " " & lastName)',
            )
        ],
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body=[
            {"firstName": "john", "lastName": "doe"},
            {"firstName": "jane", "lastName": "smith"},
        ],
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/api/users", method="POST", body={})
    response = await router.route_request(request)

    assert response.status_code == 200
    assert len(response.body) == 2
    assert response.body[0]["fullName"] == "JOHN DOE"
    assert response.body[1]["fullName"] == "JANE SMITH"


@pytest.mark.asyncio
async def test_response_transformation_jsonata_error_handling(mock_registry):
    """Test error handling for invalid JSONata expressions."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/api/test",
        connector="test",
        target_path="/test",
        response_transformations=[
            TransformationRule(
                source_field="value",
                target_field="result",
                expression="invalid {{ expression",  # Invalid syntax
            )
        ],
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200, body={"value": 123}
    )

    router = RequestRouter(registry)
    router.add_route(route_config)
    request = IntegrationRequest(route="/api/test", method="POST", body={})

    # Router catches transformation errors and logs them, but returns original response
    # (This is good production behavior - don't break requests due to transformation errors)
    response = await router.route_request(request)

    # Should return original response when transformation fails
    assert response.status_code == 200
    assert response.body == {"value": 123}  # Original body preserved
