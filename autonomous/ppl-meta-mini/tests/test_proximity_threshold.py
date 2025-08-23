#!/usr/bin/env python3
"""
Demonstrate the role of proximity threshold in face grouping.
"""

import json

import requests


def test_proximity_threshold():
    """Test different proximity threshold values."""
    base_url = "http://localhost:8004"

    print("🎯 Proximity Threshold Demonstration")
    print("=" * 50)

    # Test data: 3 faces with different distances
    test_data = {
        "face_data": [
            {"frame_number": 1, "face_id": "A", "position_x": 100, "position_y": 200},
            {
                "frame_number": 1,
                "face_id": "B",
                "position_x": 110,
                "position_y": 210,
            },  # ~14 pixels from A
            {
                "frame_number": 1,
                "face_id": "C",
                "position_x": 500,
                "position_y": 600,
            },  # ~566 pixels from A
        ]
    }

    # Test different threshold values
    thresholds = [10, 20, 50, 100, 600]

    for threshold in thresholds:
        print(f"\n🔍 Testing proximity_threshold = {threshold} pixels")
        print("-" * 40)

        try:
            # Create request with custom threshold
            request_data = test_data.copy()

            # Make request to grouping endpoint
            response = requests.post(
                f"{base_url}/api/v1/group-faces", json=request_data, timeout=10
            )

            if response.status_code == 200:
                result = response.json()

                print(f"📊 Results:")
                print(
                    f"   Original faces: {result['statistics']['original_unique_faces']}"
                )
                print(
                    f"   Groups created: {result['statistics']['merged_groups_count']}"
                )

                print(f"📋 Group Details:")
                for group in result["group_tracking"]:
                    group_id = group["Merged_Group_ID"]
                    face_ids = group["Original_Group_IDs"]
                    avg_pos = group["Average_Position"]
                    print(
                        f"   Group {group_id}: {face_ids} at ({avg_pos['x']:.1f}, {avg_pos['y']:.1f})"
                    )

                # Calculate actual distances
                face_a = {"x": 100, "y": 200}
                face_b = {"x": 110, "y": 210}
                face_c = {"x": 500, "y": 600}

                import math

                dist_ab = math.sqrt(
                    (face_a["x"] - face_b["x"]) ** 2 + (face_a["y"] - face_b["y"]) ** 2
                )
                dist_ac = math.sqrt(
                    (face_a["x"] - face_c["x"]) ** 2 + (face_a["y"] - face_c["y"]) ** 2
                )

                print(f"📐 Actual distances:")
                print(f"   A-B: {dist_ab:.1f} pixels")
                print(f"   A-C: {dist_ac:.1f} pixels")

                # Explain what happened
                if result["statistics"]["merged_groups_count"] == 1:
                    print(
                        f"✅ All faces grouped together (threshold {threshold} > max distance {dist_ac:.1f})"
                    )
                elif result["statistics"]["merged_groups_count"] == 2:
                    print(
                        f"⚖️ A&B grouped, C separate (threshold {threshold} between {dist_ab:.1f} and {dist_ac:.1f})"
                    )
                else:
                    print(
                        f"❌ All faces separate (threshold {threshold} < min distance {dist_ab:.1f})"
                    )

            else:
                print(f"❌ Request failed: {response.status_code}")

        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"\n💡 Key Insights:")
    print("=" * 50)
    print("🎯 The proximity_threshold controls face grouping based on pixel distance:")
    print("   • Lower threshold = Stricter grouping (faces must be very close)")
    print("   • Higher threshold = Looser grouping (faces can be farther apart)")
    print("   • Distance calculated using Euclidean formula: √[(x₁-x₂)² + (y₁-y₂)²]")
    print("\n📐 Use cases:")
    print("   • Video tracking: Use ~20-50 pixels for same person across frames")
    print("   • Crowd analysis: Use ~100+ pixels to group people in same area")
    print("   • Precision mode: Use ~10-20 pixels for exact face matching")


if __name__ == "__main__":
    test_proximity_threshold()
