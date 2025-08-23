#!/usr/bin/env python3
"""
Test script for PPL Meta Mini Cython compilation
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command(command, cwd=None):
    """Run a shell command and return the result."""
    print(f"Running: {command}")
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, cwd=cwd
    )

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False, result.stderr

    print(f"Output: {result.stdout}")
    return True, result.stdout


def test_cython_build():
    """Test the Cython build process."""
    print("🔧 Testing PPL Meta Mini Cython Build")
    print("=" * 50)

    # Get the directory of this script
    script_dir = Path(__file__).parent

    # Test 1: Build Cython extensions locally
    print("\n1️⃣ Testing local Cython compilation...")
    success, output = run_command(
        "python setup_cython.py build_ext --inplace", cwd=script_dir
    )

    if not success:
        print("❌ Local Cython compilation failed!")
        return False

    print("✅ Local Cython compilation successful!")

    # Test 2: Check if .so files were created
    print("\n2️⃣ Checking for compiled .so files...")
    so_files = list(script_dir.glob("**/*.so"))

    if so_files:
        print(f"✅ Found {len(so_files)} compiled .so files:")
        for so_file in so_files:
            print(f"  - {so_file}")
    else:
        print("❌ No .so files found!")
        return False

    # Test 3: Test Docker build
    print("\n3️⃣ Testing Docker build...")
    success, output = run_command(
        "docker build -f Dockerfile.cython -t ppl-meta-mini:test-cython .",
        cwd=script_dir,
    )

    if not success:
        print("❌ Docker build failed!")
        return False

    print("✅ Docker build successful!")

    # Test 4: Test container startup
    print("\n4️⃣ Testing container startup...")

    # Start container in background
    success, output = run_command(
        "docker run -d --name ppl-meta-mini-test -p 8005:8004 ppl-meta-mini:test-cython",
        cwd=script_dir,
    )

    if not success:
        print("❌ Container startup failed!")
        return False

    # Wait for container to start
    print("Waiting for container to start...")
    time.sleep(10)

    # Test health endpoint
    success, output = run_command("curl -f http://localhost:8005/health")

    if success:
        print("✅ Container is running and responding!")
    else:
        print("❌ Container health check failed!")
        # Get container logs
        run_command("docker logs ppl-meta-mini-test")

    # Cleanup
    print("\n🧹 Cleaning up...")
    run_command("docker stop ppl-meta-mini-test")
    run_command("docker rm ppl-meta-mini-test")
    run_command("docker rmi ppl-meta-mini:test-cython")

    return success


if __name__ == "__main__":
    success = test_cython_build()
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
