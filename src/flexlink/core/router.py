"""Request router for directing requests to appropriate connectors."""

import logging
import re

from flexlink.core.registry import ConnectorRegistry
from flexlink.core.transformation import TransformationEngine
from flexlink.models.request import IntegrationRequest, IntegrationResponse
from flexlink.models.transformation import RouteConfig

logger = logging.getLogger(__name__)


class RequestRouter:
    """
    Routes incoming requests to appropriate connectors.

    Matches requests to configured routes, applies transformations,
    and forwards to target connectors.
    """

    def __init__(self, registry: ConnectorRegistry):
        """
        Initialize request router.

        Args:
            registry: ConnectorRegistry containing available connectors
        """
        self.registry = registry
        self.routes: list[RouteConfig] = []

    def add_route(self, route_config: RouteConfig) -> None:
        """
        Register a route configuration.

        Args:
            route_config: Route configuration to register
        """
        self.routes.append(route_config)
        logger.info(
            f"Registered route: {route_config.method} {route_config.path} "
            f"-> {route_config.connector}"
        )

    def add_routes(self, route_configs: list[RouteConfig]) -> None:
        """
        Register multiple route configurations.

        Args:
            route_configs: List of route configurations to register
        """
        for route_config in route_configs:
            self.add_route(route_config)

    async def route_request(self, request: IntegrationRequest) -> IntegrationResponse:
        """
        Route request to appropriate connector with transformations.

        Process:
        1. Match request to configured route
        2. Get target connector from registry
        3. Apply request transformations
        4. Send request to connector
        5. Return response

        Args:
            request: Integration request to route

        Returns:
            Integration response from target connector

        Raises:
            ValueError: If no matching route found or connector not found
        """
        # Find matching route
        route_config = self._match_route(request)
        if not route_config:
            logger.warning(
                f"No route found for: {request.method} {request.route}"
            )
            return IntegrationResponse(
                status_code=404,
                error=f"No route configured for: {request.method} {request.route}"
            )

        logger.info(
            f"Matched route: {request.method} {request.route} "
            f"-> {route_config.connector}"
        )

        # Get connector
        try:
            connector = self.registry.get_connector(route_config.connector)
        except KeyError:
            logger.error(f"Connector not found: {route_config.connector}")
            return IntegrationResponse(
                status_code=500,
                error=f"Connector not found: {route_config.connector}"
            )

        # Apply request transformations
        transformed_data = request.body or {}
        if route_config.transformations:
            try:
                engine = TransformationEngine(route_config.transformations)
                transformed_data = await engine.apply(transformed_data)
                logger.debug(
                    f"Applied {len(route_config.transformations)} "
                    f"transformations to request"
                )
            except ValueError as e:
                logger.error(f"Request transformation failed: {e}")
                return IntegrationResponse(
                    status_code=400,
                    error=f"Request transformation failed: {e}"
                )

        # Extract path parameters and substitute in target path
        target_path = self._substitute_path_params(
            route_config.path, request.route, route_config.target_path
        )

        # Send request to connector
        try:
            response = await connector.send_request(
                method=request.method,
                path=target_path,
                data=transformed_data,
                headers=request.headers,
            )
            logger.info(
                f"Request routed successfully: {route_config.connector} "
                f"returned {response.status_code}"
            )

            # Apply response transformations
            if route_config.response_transformations and response.body is not None:
                try:
                    # Handle dict responses
                    if isinstance(response.body, dict):
                        engine = TransformationEngine(route_config.response_transformations)
                        response.body = await engine.apply(response.body)
                        logger.debug(
                            f"Applied {len(route_config.response_transformations)} "
                            f"transformations to response"
                        )

                    # Handle list responses - transform each item
                    elif isinstance(response.body, list):
                        engine = TransformationEngine(route_config.response_transformations)
                        transformed_items = []
                        for item in response.body:
                            if isinstance(item, dict):
                                transformed_item = await engine.apply(item)
                                transformed_items.append(transformed_item)
                            else:
                                # Non-dict items pass through unchanged
                                transformed_items.append(item)
                        response.body = transformed_items
                        logger.debug(
                            f"Applied {len(route_config.response_transformations)} "
                            f"transformations to {len(transformed_items)} response items"
                        )

                except Exception as e:
                    # Log transformation error but don't fail the request
                    logger.error(
                        f"Response transformation failed for route {route_config.path}: {str(e)}",
                        exc_info=True
                    )
                    # Return original response on transformation failure

            return response
        except Exception as e:
            logger.exception(f"Connector request failed: {e}")
            return IntegrationResponse(
                status_code=500,
                error=f"Connector request failed: {str(e)}"
            )

    def _match_route(self, request: IntegrationRequest) -> RouteConfig | None:
        """
        Find matching route configuration for request.

        Supports:
        - Exact path matching: /api/users
        - Wildcard matching: /api/users/*
        - Path parameter matching: /api/users/{id}

        Args:
            request: Integration request to match

        Returns:
            Matching RouteConfig or None if no match found
        """
        for route_config in self.routes:
            # Check HTTP method match
            if route_config.method.upper() != request.method.upper():
                continue

            # Check path match
            if self._path_matches(route_config.path, request.route):
                return route_config

        return None

    def _path_matches(self, pattern: str, path: str) -> bool:
        """
        Check if path matches pattern.

        Patterns:
        - Exact: /api/users matches /api/users
        - Wildcard: /api/users/* matches /api/users/123
        - Path params: /api/users/{id} matches /api/users/123

        Args:
            pattern: Route pattern (may contain wildcards or params)
            path: Actual request path

        Returns:
            True if path matches pattern, False otherwise
        """
        # Exact match
        if pattern == path:
            return True

        # Convert pattern to regex
        # Replace {param} with regex group
        regex_pattern = re.sub(r"\{[^}]+\}", r"([^/]+)", pattern)
        # Replace * wildcard with regex
        regex_pattern = regex_pattern.replace("*", ".*")
        # Anchor pattern
        regex_pattern = f"^{regex_pattern}$"

        # Try to match
        match = re.match(regex_pattern, path)
        return match is not None

    def _substitute_path_params(
        self, route_pattern: str, request_path: str, target_path: str
    ) -> str:
        """
        Extract path parameters from request and substitute in target path.

        Example:
        - route_pattern: /users/{id}
        - request_path: /users/123
        - target_path: /api/users/{id}
        - returns: /api/users/123

        Args:
            route_pattern: Route pattern with parameter placeholders
            request_path: Actual request path with parameter values
            target_path: Target path template to substitute parameters into

        Returns:
            Target path with parameters substituted
        """
        # Extract parameter names from route pattern
        param_names = re.findall(r"\{([^}]+)\}", route_pattern)
        if not param_names:
            # No parameters to substitute
            return target_path

        # Create regex pattern to extract values
        regex_pattern = re.sub(r"\{[^}]+\}", r"([^/]+)", route_pattern)
        regex_pattern = f"^{regex_pattern}$"

        # Extract parameter values from request path
        match = re.match(regex_pattern, request_path)
        if not match:
            # No match, return target path as-is
            return target_path

        # Build parameter value map
        param_values = match.groups()
        param_map = dict(zip(param_names, param_values))

        # Substitute parameters in target path
        result = target_path
        for param_name, param_value in param_map.items():
            result = result.replace(f"{{{param_name}}}", param_value)

        return result

    def list_routes(self) -> list[dict[str, str]]:
        """
        List all registered routes.

        Returns:
            List of route summaries
        """
        return [
            {
                "method": route.method,
                "path": route.path,
                "connector": route.connector,
                "target_path": route.target_path,
                "transformations": str(len(route.transformations))
            }
            for route in self.routes
        ]

    def clear_routes(self) -> None:
        """Clear all registered routes."""
        self.routes.clear()
        logger.info("Cleared all routes")
