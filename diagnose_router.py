#!/usr/bin/env python3
"""
Diagnostic script to identify person objects router import issues
"""

import os
import sys

sys.path.insert(0, "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/src")


def test_imports():
    print("🔍 Testing person objects router imports step by step...")

    # Test 1: Basic imports
    try:
        import sys

        print("✅ sys import: OK")
    except Exception as e:
        print(f"❌ sys import failed: {e}")
        return

    # Test 2: FastAPI import
    try:
        from fastapi import FastAPI

        print("✅ FastAPI import: OK")
    except Exception as e:
        print(f"❌ FastAPI import failed: {e}")
        return

    # Test 3: Database import
    try:
        from database import VisionDatabase

        print("✅ Database import: OK")
    except Exception as e:
        print(f"❌ Database import failed: {e}")
        print(f"Error details: {e}")
        return

    # Test 4: Person objects workflow import
    try:
        from person_objects.ppl_thread_workflow import PPLThreadWorkflowController

        print("✅ PPL Thread workflow import: OK")
    except Exception as e:
        print(f"❌ PPL Thread workflow import failed: {e}")
        import traceback

        traceback.print_exc()
        return

    # Test 5: Person objects API import
    try:
        from person_objects.person_objects_api import router as person_objects_router

        print("✅ Person objects API router import: OK")
        print(f"   Router prefix: {person_objects_router.prefix}")
        print(f"   Number of routes: {len(person_objects_router.routes)}")

        # List all routes
        print("   Routes:")
        for route in person_objects_router.routes:
            print(f"     - {route.methods} {route.path}")

    except Exception as e:
        print(f"❌ Person objects API router import failed: {e}")
        import traceback

        traceback.print_exc()
        return

    # Test 6: FastAPI app with router inclusion
    try:
        app = FastAPI()
        app.include_router(person_objects_router)
        print(
            f"✅ Router inclusion test: OK - App now has {len(app.routes)} total routes"
        )

        # Check if our endpoint is there
        for route in app.routes:
            if hasattr(route, "path") and "person-objects/media" in route.path:
                print(f"   Found session discovery route: {route.methods} {route.path}")

    except Exception as e:
        print(f"❌ Router inclusion failed: {e}")
        import traceback

        traceback.print_exc()
        return

    print("✅ All tests passed - router should work correctly")


if __name__ == "__main__":
    test_imports()
