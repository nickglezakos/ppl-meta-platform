#!/usr/bin/env python3
"""
Debug script to test and fix the person objects API issues
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

# Add the vision service path
vision_path = os.path.join(os.path.dirname(__file__), "ppl-meta-vision", "src")
sys.path.insert(0, vision_path)

import requests


def test_person_objects_health():
    """Test the person objects API health endpoint"""
    print("🔍 Testing Person Objects API Health...")

    try:
        response = requests.get(
            "http://localhost:8003/api/v1/person-objects/health", timeout=10
        )
        if response.status_code == 200:
            print("✅ Person Objects API is healthy")
            data = response.json()
            print(f"   Service: {data.get('service')}")
            print(f"   Features: {data.get('features', {})}")
            return True
        else:
            print(f"❌ Person Objects API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Person Objects API: {e}")
        return False


def test_session_status():
    """Test session status endpoint with proper timezone handling"""
    print("\n🔍 Testing Session Status Endpoint...")

    # First get available sessions
    try:
        response = requests.get("http://localhost:8003/sessions?limit=5", timeout=10)
        if response.status_code == 200:
            data = response.json()
            sessions = data.get("sessions", [])

            if not sessions:
                print("❌ No sessions found to test")
                return False

            # Test the first session
            session_uuid = sessions[0]["session_uuid"]
            print(f"   Testing session: {session_uuid}")

            # Test session status
            status_response = requests.get(
                f"http://localhost:8003/sessions/{session_uuid}/status", timeout=10
            )

            if status_response.status_code == 200:
                print("✅ Session status endpoint working")
                status_data = status_response.json()
                print(
                    f"   Status: {status_data.get('session', {}).get('processing_status')}"
                )
                return True, session_uuid
            else:
                print(f"❌ Session status failed: {status_response.status_code}")
                print(f"   Error: {status_response.text}")
                return False, None

        else:
            print(f"❌ Failed to get sessions: {response.status_code}")
            return False, None

    except Exception as e:
        print(f"❌ Session status test failed: {e}")
        return False, None


def test_simple_person_objects_workflow():
    """Test a simple person objects workflow with a session that has face data"""
    print("\n🔍 Testing Simple Person Objects Workflow...")

    # Get sessions and find one with face data
    try:
        response = requests.get("http://localhost:8003/sessions?limit=10", timeout=10)
        if response.status_code == 200:
            data = response.json()
            sessions = data.get("sessions", [])

            # Find a session with faces
            target_session = None
            for session in sessions:
                if session.get("total_faces_detected", 0) > 0:
                    target_session = session
                    break

            if not target_session:
                print("❌ No sessions with face data found")
                return False

            session_uuid = target_session["session_uuid"]
            face_count = target_session.get("total_faces_detected", 0)

            print(f"   Using session: {session_uuid}")
            print(f"   Face count: {face_count}")

            # Create a full workflow request with quality analysis enabled
            workflow_request = {
                "session_uuid": session_uuid,
                "tolerance_percent": 20.0,  # Standard tolerance
                "enable_quality_analysis": True,  # Enable full quality analysis
                "enable_age_detection": False,
                "workflow_metadata": {
                    "description": "Full workflow test with quality analysis",
                    "test_mode": True,
                },
            }

            # Make the workflow request
            headers = {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU4Nzg4NjIyfQ.OAN0wiaIgspfB8CKwP6bwagqbbN-AjbqX7Kvu8GVNRQ",
                "Content-Type": "application/json",
            }

            workflow_response = requests.post(
                "http://localhost:8003/api/v1/person-objects/workflows/start",
                json=workflow_request,
                headers=headers,
                timeout=30,
            )

            if workflow_response.status_code == 200:
                print("✅ Person Objects Workflow succeeded")
                result = workflow_response.json()
                print(f"   Workflow ID: {result.get('workflow_id', 'N/A')}")
                print(f"   Persons created: {len(result.get('person_objects', []))}")
                return True
            else:
                print(
                    f"❌ Person Objects Workflow failed: {workflow_response.status_code}"
                )
                print(f"   Error: {workflow_response.text}")
                return False

        else:
            print(
                f"❌ Failed to get sessions for workflow test: {response.status_code}"
            )
            return False

    except Exception as e:
        print(f"❌ Person objects workflow test failed: {e}")
        return False


def test_direct_database_connection():
    """Test direct database connection to identify timezone issues"""
    print("\n🔍 Testing Direct Database Connection...")

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # Use the same connection parameters as the vision service
        conn_params = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "ppl_vision_db"),
            "user": os.getenv("DB_USER", "nickgklezakos"),
            "password": os.getenv("DB_PASSWORD", "change-this-password"),
        }

        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Test basic query
        cursor.execute("SELECT NOW() as current_time")
        result = cursor.fetchone()
        print(f"✅ Database connection successful")
        print(f"   Current DB time: {result['current_time']}")

        # Check for sessions table and data
        cursor.execute(
            """
            SELECT COUNT(*) as session_count 
            FROM face_detection_sessions 
            WHERE total_faces_detected > 0
        """
        )
        session_result = cursor.fetchone()
        print(f"   Sessions with faces: {session_result['session_count']}")

        # Check face detections
        cursor.execute("SELECT COUNT(*) as face_count FROM face_detections")
        face_result = cursor.fetchone()
        print(f"   Total face detections: {face_result['face_count']}")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def main():
    """Run all debug tests"""
    print("🐛 PPL Meta Vision Service - Person Objects API Debug")
    print("=" * 60)

    # Test 1: Health check
    health_ok = test_person_objects_health()

    # Test 2: Database connection
    db_ok = test_direct_database_connection()

    # Test 3: Session status (to debug timezone issues)
    session_ok, session_uuid = test_session_status()

    # Test 4: Simple person objects workflow
    if session_ok and db_ok:
        workflow_ok = test_simple_person_objects_workflow()
    else:
        workflow_ok = False
        print("\n⚠️ Skipping workflow test due to previous failures")

    # Summary
    print("\n" + "=" * 60)
    print("🎯 Debug Results Summary:")
    print(f"   Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"   Database: {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"   Session Status: {'✅ PASS' if session_ok else '❌ FAIL'}")
    print(f"   Workflow: {'✅ PASS' if workflow_ok else '❌ FAIL'}")

    if health_ok and db_ok and session_ok and workflow_ok:
        print("\n🎉 All tests passed! Person Objects API is working.")
    else:
        print("\n🔧 Issues found. Check the logs above for details.")

    return all([health_ok, db_ok, session_ok, workflow_ok])


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
