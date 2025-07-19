#!/usr/bin/env python3
"""
Test script for Issue #015 - Media Variants and Versions Manageme            variant_data = {
                "file_path": f"/variants/{self.test_media_id}/thumbnail.jpg",
                "filename": "thumbnail.jpg            generation_request = {
                "variant_types": ["thumbnail_small", "thumbnail_medium"],
                "quality_levels": ["low", "medium"]
            }               "file_size": 2048,
                "mime_type": "image/jpeg",
                "variant_type": "thumbnail_medium",
                "quality_level": "medium",
                "metadata": {
                    "width": 200,
                    "height": 200,
                    "generated_at": "2024-01-15T10:30:00Z"
                }
            }ipt tests the comprehensive variant management functionality
including CRUD operations, automatic generation, and statistics.
"""

import json
import time
from typing import Any, Dict

import requests


class VariantManagementTest:
    """Test class for media variant management functionality."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        self.test_media_id = None
        self.test_variant_id = None

    def test_health_check(self) -> bool:
        """Test service health."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            print(f"📋 Health Check: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

    def create_test_media(self) -> bool:
        """Create test media file for variant testing."""
        try:
            # Create a simple test file
            test_file_content = b"Test media content for variant testing"

            files = {"file": ("test_media.txt", test_file_content, "text/plain")}
            data = {
                "media_type": "document",  # Required field
                "user_id": self.test_user_id,
                "title": "Test Media for Variants",
                "description": "Media file for testing variant management",
                "is_public": True,
            }

            response = requests.post(
                f"{self.base_url}/api/v1/media/upload",
                files=files,
                data=data,
                timeout=10,
            )

            if response.status_code == 200:
                media_data = response.json()
                self.test_media_id = str(media_data["id"])
                print(f"✅ Test media created: {self.test_media_id}")
                return True
            else:
                print(f"❌ Failed to create test media: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error creating test media: {e}")
            return False

    def test_get_variant_types(self) -> bool:
        """Test getting available variant types."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/media/variants/types", timeout=5
            )

            if response.status_code == 200:
                variant_types = response.json()
                print(f"✅ Variant types retrieved: {variant_types}")
                return len(variant_types) > 0
            else:
                print(f"❌ Failed to get variant types: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error getting variant types: {e}")
            return False

    def test_create_variant(self) -> bool:
        """Test creating a media variant."""
        try:
            variant_data = {
                "file_path": f"/variants/{self.test_media_id}/thumbnail.jpg",
                "filename": "thumbnail.jpg",
                "file_size": 2048,
                "mime_type": "image/jpeg",
                "variant_type": "thumbnail_medium",
                "quality_level": "medium",
                "metadata": {
                    "width": 200,
                    "height": 200,
                    "generated_at": "2024-01-15T10:30:00Z",
                },
            }

            response = requests.post(
                f"{self.base_url}/api/v1/media/{self.test_media_id}/variants",
                json=variant_data,
                params={"user_id": self.test_user_id},
                timeout=10,
            )

            if response.status_code == 200:
                variant = response.json()
                self.test_variant_id = str(variant["id"])
                print(f"✅ Variant created: {self.test_variant_id}")
                return True
            else:
                print(f"❌ Failed to create variant: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error creating variant: {e}")
            return False

    def test_get_media_variants(self) -> bool:
        """Test getting all variants for a media file."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/media/{self.test_media_id}/variants",
                params={"user_id": self.test_user_id},
                timeout=5,
            )

            if response.status_code == 200:
                variants = response.json()
                print(f"✅ Retrieved {len(variants)} variants")
                return len(variants) > 0
            else:
                print(f"❌ Failed to get variants: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error getting variants: {e}")
            return False

    def test_get_variant_details(self) -> bool:
        """Test getting detailed variant information."""
        if not self.test_variant_id:
            print("❌ No variant ID available for testing")
            return False

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/media/{self.test_media_id}/variants/{self.test_variant_id}",
                params={"user_id": self.test_user_id},
                timeout=5,
            )

            if response.status_code == 200:
                variant = response.json()
                print(f"✅ Variant details retrieved: {variant['variant_type']}")
                return True
            else:
                print(f"❌ Failed to get variant details: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error getting variant details: {e}")
            return False

    def test_update_variant(self) -> bool:
        """Test updating a variant."""
        if not self.test_variant_id:
            print("❌ No variant ID available for testing")
            return False

        try:
            update_data = {"width": 300, "height": 300, "quality": "high"}

            response = requests.put(
                f"{self.base_url}/api/v1/media/{self.test_media_id}/variants/{self.test_variant_id}",
                json=update_data,
                params={"user_id": self.test_user_id},
                timeout=10,
            )

            if response.status_code == 200:
                variant = response.json()
                print(f"✅ Variant updated successfully")
                return True
            else:
                print(f"❌ Failed to update variant: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error updating variant: {e}")
            return False

    def test_variant_statistics(self) -> bool:
        """Test getting variant statistics."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/media/{self.test_media_id}/variants/statistics",
                params={"user_id": self.test_user_id},
                timeout=5,
            )

            if response.status_code == 200:
                stats = response.json()
                print(f"✅ Variant statistics: {stats['total_variants']} variants")
                return True
            else:
                print(f"❌ Failed to get variant statistics: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error getting variant statistics: {e}")
            return False

    def test_generate_variants(self) -> bool:
        """Test generating standard variants."""
        try:
            generation_request = {
                "variant_types": ["thumbnail_small", "thumbnail_medium"],
                "quality_levels": ["low", "medium"],
            }

            response = requests.post(
                f"{self.base_url}/api/v1/media/{self.test_media_id}/variants/generate",
                json=generation_request,
                params={"user_id": self.test_user_id},
                timeout=15,
            )

            if response.status_code == 200:
                variants = response.json()
                print(f"✅ Generated {len(variants)} variants")
                return len(variants) > 0
            else:
                print(f"❌ Failed to generate variants: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error generating variants: {e}")
            return False

    def test_delete_variant(self) -> bool:
        """Test deleting a variant."""
        if not self.test_variant_id:
            print("❌ No variant ID available for testing")
            return False

        try:
            response = requests.delete(
                f"{self.base_url}/api/v1/media/{self.test_media_id}/variants/{self.test_variant_id}",
                params={"user_id": self.test_user_id},
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Variant deleted: {result['message']}")
                return True
            else:
                print(f"❌ Failed to delete variant: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error deleting variant: {e}")
            return False

    def cleanup_test_media(self) -> bool:
        """Clean up test media."""
        if not self.test_media_id:
            return True

        try:
            response = requests.delete(
                f"{self.base_url}/api/v1/media/{self.test_media_id}",
                params={"user_id": self.test_user_id},
                timeout=10,
            )

            if response.status_code == 200:
                print(f"✅ Test media cleaned up")
                return True
            else:
                print(f"⚠️ Failed to cleanup test media: {response.status_code}")
                return False

        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")
            return False

    def run_comprehensive_test(self) -> Dict[str, bool]:
        """Run comprehensive variant management tests."""
        print("🚀 Starting Issue #015 - Media Variants Management Tests")
        print("=" * 60)

        results = {}

        # Test service health
        results["health_check"] = self.test_health_check()
        if not results["health_check"]:
            print("❌ Service not available - stopping tests")
            return results

        # Create test media
        results["create_test_media"] = self.create_test_media()
        if not results["create_test_media"]:
            print("❌ Cannot create test media - stopping tests")
            return results

        # Test variant functionality
        results["get_variant_types"] = self.test_get_variant_types()
        results["create_variant"] = self.test_create_variant()
        results["get_media_variants"] = self.test_get_media_variants()
        results["get_variant_details"] = self.test_get_variant_details()
        results["update_variant"] = self.test_update_variant()
        results["variant_statistics"] = self.test_variant_statistics()
        results["generate_variants"] = self.test_generate_variants()
        results["delete_variant"] = self.test_delete_variant()

        # Cleanup
        results["cleanup"] = self.cleanup_test_media()

        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY:")
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        print(f"✅ Passed: {passed}/{total}")

        if passed == total:
            print("🎉 All variant management tests PASSED!")
        else:
            print("❌ Some tests FAILED - check implementation")
            for test_name, result in results.items():
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"  {test_name}: {status}")

        return results


if __name__ == "__main__":
    tester = VariantManagementTest()
    results = tester.run_comprehensive_test()
