#!/usr/bin/env python3
"""
Test script to verify person objects router registration
"""

import os
import sys

sys.path.insert(0, "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/src")

try:
    from fastapi import FastAPI
    from person_objects.person_objects_api import router as person_objects_router

    # Create a test app
    test_app = FastAPI()

    print("✅ Successfully imported person objects router")
    print(f"Router prefix: {person_objects_router.prefix}")
    print(f"Router tags: {person_objects_router.tags}")
    print(f"Number of routes: {len(person_objects_router.routes)}")

    print("\nRoutes:")
    for route in person_objects_router.routes:
        print(f"  - {route.methods} {route.path}")

    # Include the router
    test_app.include_router(person_objects_router)

    print(f"\nAfter including router, app has {len(test_app.routes)} total routes:")
    for route in test_app.routes:
        if hasattr(route, "methods"):
            print(f"  - {route.methods} {route.path}")
        else:
            print(f"  - {type(route)} {getattr(route, 'path', 'N/A')}")

    print("\n✅ Router inclusion test successful")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
