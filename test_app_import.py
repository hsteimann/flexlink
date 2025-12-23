#!/usr/bin/env python3
"""Test that the FastAPI app can be imported and configured correctly."""

import sys


def test_app_import():
    """Test importing the FastAPI application."""
    print("=" * 60)
    print("CHECKPOINT GAMMA - App Import Test")
    print("=" * 60)
    print()

    errors = []

    # Test 1: Import main module
    print("✓ Testing import of flexlink.main...")
    try:
        from flexlink import main

        print("  ✅ Successfully imported flexlink.main")
    except Exception as e:
        errors.append(f"Failed to import flexlink.main: {e}")
        print(f"  ❌ Failed to import flexlink.main: {e}")
        return False

    # Test 2: Check app instance
    print("\n✓ Testing FastAPI app instance...")
    try:
        app = main.app
        assert app is not None
        print(f"  ✅ App instance created: {app.title}")
    except Exception as e:
        errors.append(f"Failed to access app: {e}")
        print(f"  ❌ Failed to access app: {e}")

    # Test 3: Check routers included
    print("\n✓ Testing routers included...")
    try:
        routes = [route.path for route in app.routes]
        required_routes = [
            "/",
            "/health",
            "/health/detailed",
            "/api/v1/route",
            "/api/v1/connectors",
            "/api/v1/routes",
            "/api/v1/files/upload",
            "/api/v1/files/convert",
            "/api/v1/files/formats",
        ]

        for route_path in required_routes:
            if route_path in routes:
                print(f"  ✅ Route registered: {route_path}")
            else:
                errors.append(f"Missing route: {route_path}")
                print(f"  ❌ Missing route: {route_path}")

    except Exception as e:
        errors.append(f"Failed to check routes: {e}")
        print(f"  ❌ Failed to check routes: {e}")

    # Test 4: Check middleware
    print("\n✓ Testing middleware...")
    try:
        middleware_count = len(app.user_middleware)
        assert middleware_count >= 2  # ErrorHandling + Logging
        print(f"  ✅ Middleware configured: {middleware_count} middleware(s)")
    except Exception as e:
        errors.append(f"Failed to check middleware: {e}")
        print(f"  ❌ Failed to check middleware: {e}")

    # Test 5: Check OpenAPI schema
    print("\n✓ Testing OpenAPI schema generation...")
    try:
        openapi_schema = app.openapi()
        assert "info" in openapi_schema
        assert "paths" in openapi_schema
        assert openapi_schema["info"]["title"] == "FlexLink Middleware"
        print(f"  ✅ OpenAPI schema: {openapi_schema['info']['title']} v{openapi_schema['info']['version']}")
    except Exception as e:
        errors.append(f"Failed to generate OpenAPI schema: {e}")
        print(f"  ❌ Failed to generate OpenAPI schema: {e}")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ APP IMPORT TEST FAILED")
        print(f"   {len(errors)} error(s) found:")
        for error in errors:
            print(f"   - {error}")
        print("=" * 60)
        return False
    else:
        print("✅ APP IMPORT TEST PASSED")
        print("   All components properly configured!")
        print("=" * 60)
        return True


if __name__ == "__main__":
    result = test_app_import()
    sys.exit(0 if result else 1)
