#!/usr/bin/env python3
"""
Debug script to check orchestrator service configuration and token generation
"""
import os
import sys

# Add the src directory to Python path
sys.path.insert(
    0, "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-orchestrator/src"
)


def check_environment():
    """Check environment configuration"""
    print("🔍 Environment Check:")
    print("-" * 40)

    # Check if NODE_SERVICE_SECRET is in environment
    node_secret = os.getenv("NODE_SERVICE_SECRET")
    if node_secret:
        print(f"✅ NODE_SERVICE_SECRET found in environment: {node_secret[:10]}...")
    else:
        print("❌ NODE_SERVICE_SECRET not found in environment")

    print()


def check_config():
    """Check orchestrator configuration"""
    print("🔍 Orchestrator Config Check:")
    print("-" * 40)

    try:
        from config import settings

        print(f"✅ Config imported successfully")
        print(
            f"✅ NODE_SERVICE_SECRET from settings: {settings.NODE_SERVICE_SECRET[:10]}..."
        )
        return settings.NODE_SERVICE_SECRET
    except Exception as e:
        print(f"❌ Failed to import config: {e}")
        return None


def test_token_generation(secret):
    """Test token generation with the secret"""
    print("🔍 Token Generation Test:")
    print("-" * 40)

    try:
        from service_auth import service_auth

        print("✅ ServiceAuth imported successfully")

        # Create a test token
        test_user_id = "test_user_123"
        token = service_auth.create_service_token(test_user_id)
        print(f"✅ Token generated: {token[:50]}...")

        # Try to verify the token
        payload = service_auth.verify_service_token(token)
        if payload:
            print(f"✅ Token verified: {payload}")
        else:
            print("❌ Token verification failed")

        return token

    except Exception as e:
        print(f"❌ Token generation failed: {e}")
        return None


def main():
    print("🚀 PPL Meta Orchestrator - Authentication Debug")
    print("=" * 60)
    print()

    # Check environment
    check_environment()

    # Check config
    secret = check_config()
    print()

    # Test token generation
    if secret:
        test_token_generation(secret)
    else:
        print("❌ Cannot test token generation without secret")


if __name__ == "__main__":
    main()
