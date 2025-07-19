#!/usr/bin/env python3
"""
Simple test for Issue #015 - Variant endpoint functionality.
Tests only the variant endpoints assuming media already exists.
"""

import requests


def test_variant_types():
    """Test getting available variant types."""
    try:
        response = requests.get("http://localhost:8000/api/v1/media/variants/types")
        print(f"Variant Types Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Available variant types: {data}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error testing variant types: {e}")
        return False


def test_media_list():
    """Test getting media list to find existing media."""
    try:
        response = requests.get("http://localhost:8000/api/v1/media/search")
        print(f"Media Search Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} media files")
            if data:
                print(f"First media: {data[0]['id']} - {data[0]['title']}")
            return data
        else:
            print(f"Error: {response.text}")
            return []
    except Exception as e:
        print(f"Error getting media list: {e}")
        return []


def test_get_variants(media_id: str, user_id: str):
    """Test getting variants for a media file."""
    try:
        response = requests.get(
            f"http://localhost:8000/api/v1/media/{media_id}/variants",
            params={"user_id": user_id},
        )
        print(f"Get Variants Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} variants for media {media_id}")
            return data
        else:
            print(f"Error: {response.text}")
            return []
    except Exception as e:
        print(f"Error getting variants: {e}")
        return []


if __name__ == "__main__":
    print("🧪 Simple Variant Endpoints Test")
    print("=" * 40)

    # Test variant types endpoint
    print("\n1. Testing variant types...")
    test_variant_types()

    # Test media search
    print("\n2. Testing media search...")
    media_list = test_media_list()

    # If we have media, test variants
    if media_list:
        media_id = str(media_list[0]["id"])
        user_id = str(media_list[0]["uploaded_by"])
        print(f"\n3. Testing variants for media {media_id}...")
        test_get_variants(media_id, user_id)
    else:
        print("\n3. No media found to test variants")

    print("\n✅ Simple test completed")
