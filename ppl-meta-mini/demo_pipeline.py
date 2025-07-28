#!/usr/bin/env python3
"""
Demonstration of the complete video analysis pipeline.
"""

import json

import requests


def demo_complete_pipeline():
    """Demonstrate the complete video analysis pipeline."""
    base_url = "http://localhost:8004"

    print("🎬 PPL Meta Mini - Complete Video Analysis Demo")
    print("=" * 50)

    # Test the face grouping with demo data first
    print("\n1️⃣ Testing Face Grouping with Demo Data...")

    try:
        # Get demo data
        demo_response = requests.get(f"{base_url}/api/v1/demo-data", timeout=10)
        if demo_response.status_code == 200:
            demo_result = demo_response.json()
            demo_data = demo_result["data"]  # Note: using "data" not "demo_data"

            print(f"✅ Got {len(demo_data)} demo face detections")

            # Convert to required format for grouping
            face_data = []
            for item in demo_data:
                face_data.append(
                    {
                        "frame_number": item["Frame_Number"],
                        "face_id": item["Face_ID"],
                        "position_x": item["Position_X"],
                        "position_y": item["Position_Y"],
                    }
                )

            # Test grouping
            grouping_request = {"face_data": face_data}
            group_response = requests.post(
                f"{base_url}/api/v1/group-faces", json=grouping_request, timeout=30
            )

            if group_response.status_code == 200:
                result = group_response.json()
                print("✅ Face grouping successful!")

                # Display results
                if "summary" in result:
                    summary = result["summary"]
                    print(f"   📊 Groups created: {summary.get('total_groups', 'N/A')}")
                    print(
                        f"   👥 Faces processed: {summary.get('faces_processed', 'N/A')}"
                    )

                if "group_tracking" in result:
                    print("\n   📋 Group Mapping:")
                    for group in result["group_tracking"]:
                        group_id = group.get("Merged_Group_ID", "Unknown")
                        original_ids = group.get("Original_Group_IDs", [])
                        print(f"      Group {group_id}: {original_ids}")

                print("\n   🎯 This demonstrates the pipeline:")
                print("      1. ✅ Face detection data received")
                print("      2. ✅ Advanced grouping algorithm applied")
                print("      3. ✅ Merged groups with proximity clustering")
                print("      4. ✅ Complete analysis returned")

            else:
                print(f"❌ Grouping failed: {group_response.status_code}")
                print(group_response.text)

    except Exception as e:
        print(f"❌ Demo error: {e}")

    print("\n2️⃣ Video Analysis Pipeline Ready!")
    print("=" * 50)
    print("🎬 For video analysis, use:")
    print(f"   curl -X POST {base_url}/api/v1/complete-video-analysis \\")
    print("        -F 'file=@your_video.mp4' \\")
    print("        -F 'max_faces_per_frame=10' \\")
    print("        -F 'proximity_threshold=50'")

    print("\n📊 The complete pipeline will:")
    print("   1. 🎥 Process your uploaded video")
    print("   2. 👁️  Detect faces in every frame")
    print("   3. 🎯 Group similar faces together")
    print("   4. 📈 Return complete analysis with:")
    print("      • Video metadata (fps, duration, etc.)")
    print("      • Face detection statistics")
    print("      • Merged face groups")
    print("      • Processing pipeline status")

    print(f"\n🌐 API Documentation: {base_url}/docs")
    print("   View all endpoints and test them interactively!")


if __name__ == "__main__":
    demo_complete_pipeline()
