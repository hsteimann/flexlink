#!/usr/bin/env python3
"""Verification script for CHECKPOINT GAMMA."""

import asyncio
import sys

import httpx


async def verify_checkpoint_gamma():
    """Verify all CHECKPOINT GAMMA requirements."""
    print("=" * 60)
    print("CHECKPOINT GAMMA VERIFICATION")
    print("=" * 60)
    print()

    base_url = "http://localhost:8000"
    errors = []

    async with httpx.AsyncClient() as client:
        # Test 1: Root endpoint
        print("✓ Testing root endpoint...")
        try:
            response = await client.get(f"{base_url}/")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "version" in data
            print(f"  ✅ Root: {data['message']} v{data['version']}")
        except Exception as e:
            errors.append(f"Root endpoint failed: {e}")
            print(f"  ❌ Root endpoint failed: {e}")

        # Test 2: Health check
        print("\n✓ Testing health check...")
        try:
            response = await client.get(f"{base_url}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            print(f"  ✅ Health: {data['status']}")
        except Exception as e:
            errors.append(f"Health check failed: {e}")
            print(f"  ❌ Health check failed: {e}")

        # Test 3: Detailed health check
        print("\n✓ Testing detailed health check...")
        try:
            response = await client.get(f"{base_url}/health/detailed")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "system" in data
            assert "components" in data
            print(f"  ✅ Detailed health: {data['status']}")
            print(f"     Platform: {data['system']['platform']}")
            print(f"     Python: {data['system']['python_version']}")
            print(
                f"     Connectors: {data['components']['connectors']['count']}"
            )
        except Exception as e:
            errors.append(f"Detailed health check failed: {e}")
            print(f"  ❌ Detailed health check failed: {e}")

        # Test 4: List connectors
        print("\n✓ Testing connector listing...")
        try:
            response = await client.get(f"{base_url}/api/v1/connectors")
            assert response.status_code == 200
            data = response.json()
            assert "connectors" in data
            print(f"  ✅ Connectors: {len(data['connectors'])} registered")
        except Exception as e:
            errors.append(f"Connector listing failed: {e}")
            print(f"  ❌ Connector listing failed: {e}")

        # Test 5: List routes
        print("\n✓ Testing route listing...")
        try:
            response = await client.get(f"{base_url}/api/v1/routes")
            assert response.status_code == 200
            data = response.json()
            assert "routes" in data
            print(f"  ✅ Routes: {len(data['routes'])} configured")
        except Exception as e:
            errors.append(f"Route listing failed: {e}")
            print(f"  ❌ Route listing failed: {e}")

        # Test 6: List file formats
        print("\n✓ Testing file format listing...")
        try:
            response = await client.get(f"{base_url}/api/v1/files/formats")
            assert response.status_code == 200
            data = response.json()
            assert "formats" in data
            assert "csv" in data["formats"]
            assert "json" in data["formats"]
            assert "xml" in data["formats"]
            print(f"  ✅ File formats: {', '.join(data['formats'])}")
        except Exception as e:
            errors.append(f"File format listing failed: {e}")
            print(f"  ❌ File format listing failed: {e}")

        # Test 7: File upload (CSV)
        print("\n✓ Testing file upload (CSV)...")
        try:
            csv_content = b"id,name,email\n1,John,john@test.com\n2,Jane,jane@test.com"
            files = {"file": ("test.csv", csv_content, "text/csv")}
            params = {"source_format": "csv"}

            response = await client.post(
                f"{base_url}/api/v1/files/upload", params=params, files=files
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["records_processed"] == 2
            print(
                f"  ✅ File upload: {data['records_processed']} records processed"
            )
        except Exception as e:
            errors.append(f"File upload failed: {e}")
            print(f"  ❌ File upload failed: {e}")

        # Test 8: File conversion (CSV → JSON)
        print("\n✓ Testing file conversion (CSV → JSON)...")
        try:
            csv_content = b"id,name\n1,Alice\n2,Bob"
            files = {"file": ("test.csv", csv_content, "text/csv")}
            params = {"source_format": "csv", "target_format": "json"}

            response = await client.post(
                f"{base_url}/api/v1/files/convert", params=params, files=files
            )
            assert response.status_code == 200
            assert b'"id"' in response.content
            assert b"Alice" in response.content
            print("  ✅ File conversion: CSV → JSON successful")
        except Exception as e:
            errors.append(f"File conversion failed: {e}")
            print(f"  ❌ File conversion failed: {e}")

        # Test 9: OpenAPI docs
        print("\n✓ Testing OpenAPI documentation...")
        try:
            response = await client.get(f"{base_url}/docs")
            assert response.status_code == 200
            print("  ✅ OpenAPI docs: Available at /docs")
        except Exception as e:
            errors.append(f"OpenAPI docs failed: {e}")
            print(f"  ❌ OpenAPI docs failed: {e}")

        # Test 10: OpenAPI JSON schema
        print("\n✓ Testing OpenAPI JSON schema...")
        try:
            response = await client.get(f"{base_url}/openapi.json")
            assert response.status_code == 200
            data = response.json()
            assert "info" in data
            assert "paths" in data
            print(f"  ✅ OpenAPI schema: {data['info']['title']} v{data['info']['version']}")
        except Exception as e:
            errors.append(f"OpenAPI schema failed: {e}")
            print(f"  ❌ OpenAPI schema failed: {e}")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ CHECKPOINT GAMMA VERIFICATION FAILED")
        print(f"   {len(errors)} error(s) found:")
        for error in errors:
            print(f"   - {error}")
        print("=" * 60)
        return False
    else:
        print("✅ CHECKPOINT GAMMA VERIFICATION PASSED")
        print("   All endpoints working correctly!")
        print("=" * 60)
        return True


if __name__ == "__main__":
    print("\nMake sure the server is running:")
    print("  uvicorn flexlink.main:app --reload")
    print()

    result = asyncio.run(verify_checkpoint_gamma())
    sys.exit(0 if result else 1)
