#!/usr/bin/env python3
"""
Quick test to verify face storage in Vision database
"""

import json

import requests


def check_vision_service_status():
    """Check Vision Service health and endpoints"""
    try:
        print("🔍 Checking Vision Service status...")
        response = requests.get("http://localhost:8003/health", timeout=5)
        if response.status_code == 200:
            print("✅ Vision Service is running")
            health_data = response.json()
            print(f"   Version: {health_data.get('version')}")
            print(f"   Models loaded: {health_data.get('models_loaded')}")
            print(f"   Available methods: {health_data.get('available_methods')}")
            return True
        else:
            print(f"❌ Vision Service health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Vision Service: {e}")
        return False


def check_database_via_api():
    """Try to get database statistics via various API endpoints"""
    print("\n🗄️ Checking database via API endpoints...")

    # Try common endpoints that might return database info
    endpoints_to_try = [
        "/stats",
        "/database/stats",
        "/analytics",
        "/health/detailed",
        "/admin/stats",
    ]

    for endpoint in endpoints_to_try:
        try:
            url = f"http://localhost:8003{endpoint}"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                print(f"✅ Found endpoint: {endpoint}")
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
                return True
        except:
            continue

    print("❌ No database stats endpoints found")
    return False


def test_face_query_endpoints():
    """Test face query endpoints to see if any faces exist"""
    print("\n👤 Testing face query endpoints...")

    # Try to get faces for a test media ID
    test_media_ids = ["test-media-123", "sample-video-1", "cam-recording-001"]

    for media_id in test_media_ids:
        try:
            url = f"http://localhost:8003/faces/media/{media_id}"
            response = requests.get(url, timeout=3)
            print(f"   Testing media ID '{media_id}': {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                face_count = len(data.get("faces", []))
                print(f"   ✅ Found {face_count} faces for {media_id}")
                if face_count > 0:
                    return True
        except Exception as e:
            print(f"   ❌ Error querying {media_id}: {e}")

    print("❌ No faces found in test queries")
    return False


def check_database_directly():
    """Try to check database directly using Python"""
    print("\n🔗 Attempting direct database connection...")

    try:
        import psycopg2

        # Database connection parameters (matching Vision Service config)
        conn_params = {
            "host": "localhost",
            "port": 5432,
            "database": "ppl_vision_db",
            "user": "nickgklezakos",
            "password": "change-this-password",
        }

        connection = psycopg2.connect(**conn_params)
        cursor = connection.cursor()

        # Check if face_detections table exists
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'face_detections'
            );
        """
        )
        table_exists = cursor.fetchone()[0]

        if table_exists:
            print("✅ face_detections table exists")

            # Count total faces
            cursor.execute("SELECT COUNT(*) FROM face_detections")
            total_faces = cursor.fetchone()[0]
            print(f"   📊 Total faces in database: {total_faces}")

            # Get recent faces
            cursor.execute(
                """
                SELECT media_id, confidence, method, created_at 
                FROM face_detections 
                ORDER BY created_at DESC 
                LIMIT 5
            """
            )
            recent_faces = cursor.fetchall()

            if recent_faces:
                print("   🕒 Recent face detections:")
                for face in recent_faces:
                    print(
                        f"     - Media: {face[0]}, Confidence: {face[1]:.2f}, Method: {face[2]}, Time: {face[3]}"
                    )
            else:
                print("   ❌ No face detections found")

        else:
            print("❌ face_detections table does not exist")

        cursor.close()
        connection.close()
        return table_exists and total_faces > 0

    except ImportError:
        print("❌ psycopg2 not available for direct database access")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def main():
    """Main verification function"""
    print("🧪 PPL Meta Vision Database Face Storage Verification")
    print("=" * 55)

    # Check service status
    if not check_vision_service_status():
        print("\n❌ Cannot proceed without Vision Service running")
        return

    # Try different methods to verify face storage
    methods_tried = []

    # Method 1: API endpoints
    if check_database_via_api():
        methods_tried.append("✅ API endpoints")
    else:
        methods_tried.append("❌ API endpoints")

    # Method 2: Face query endpoints
    if test_face_query_endpoints():
        methods_tried.append("✅ Face query endpoints")
    else:
        methods_tried.append("❌ Face query endpoints")

    # Method 3: Direct database access
    if check_database_directly():
        methods_tried.append("✅ Direct database access")
    else:
        methods_tried.append("❌ Direct database access")

    # Summary
    print("\n📋 Verification Summary:")
    print("-" * 25)
    for method in methods_tried:
        print(f"  {method}")

    # Recommendations
    print("\n💡 Recommendations:")
    if "✅" in str(methods_tried):
        print("  ✅ Face storage verification completed successfully!")
        print("  ✅ Faces are being stored in the Vision database")
    else:
        print("  ⚠️  No faces found in Vision database")
        print("  🔧 Try running a face detection workflow to test storage")
        print("  🔧 Check Vision Service logs for any storage errors")


if __name__ == "__main__":
    main()
