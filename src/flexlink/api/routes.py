"""REST API routes for integration requests."""

from fastapi import APIRouter, Depends, Response

from flexlink.api.dependencies import get_router
from flexlink.core.router import RequestRouter
from flexlink.models.request import IntegrationRequest, IntegrationResponse

router = APIRouter(prefix="/v1", tags=["integration"])


@router.post("/route", response_model=IntegrationResponse)
async def route_request(
    request: IntegrationRequest,
    http_response: Response,
    request_router: RequestRouter = Depends(get_router),
) -> IntegrationResponse:
    """
    Route a request to the appropriate connector.

    The request will be:
    1. Matched to a configured route
    2. Transformed according to route rules
    3. Sent to the target connector
    4. Response returned

    Args:
        request: Integration request with route, method, and body
        http_response: FastAPI Response object to set HTTP status code
        request_router: RequestRouter dependency

    Returns:
        Integration response from target connector

    Note:
        The HTTP status code of the response will match the status_code
        field in the IntegrationResponse body for proper HTTP semantics.
    """
    integration_response = await request_router.route_request(request)

    # Set actual HTTP status code to match integration result
    http_response.status_code = integration_response.status_code

    return integration_response


# Connector listing moved to dedicated connectors.py module
# See: flexlink.api.connectors for the full connector metadata endpoint


@router.get("/routes")
async def list_routes(
    request_router: RequestRouter = Depends(get_router),
) -> dict[str, list[dict[str, str]]]:
    """
    List all registered routes.

    Args:
        request_router: RequestRouter dependency

    Returns:
        Dictionary with list of route configurations
    """
    routes = request_router.list_routes()
    return {"routes": routes}
