#!/usr/bin/env python3
"""
Quick verification script for PPL Meta Mini Cython build prerequisites
"""

import importlib.util
import subprocess
import sys


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")

    if version >= (3, 8):
        print("✅ Python version is compatible")
        return True
    else:
        print("❌ Python version too old (need >= 3.8)")
        return False


def check_required_modules():
    """Check if required modules can be imported."""
    required_modules = [
        "setuptools",
        "wheel",
    ]

    optional_modules = [
        "Cython",
        "fastapi",
        "uvicorn",
        "pydantic",
        "pandas",
        "plotly",
        "cv2",  # opencv-python
    ]

    print("\nChecking required modules:")
    all_good = True

    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - REQUIRED")
            all_good = False

    print("\nChecking optional modules:")
    for module in optional_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"⚠️  {module} - will be installed during build")

    return all_good


def check_docker():
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True, check=True
        )
        print(f"\n✅ Docker: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n❌ Docker not available")
        return False


def check_source_files():
    """Check if source files exist."""
    from pathlib import Path

    required_files = [
        "src/main.py",
        "src/api/analytics.py",
        "requirements.txt",
    ]

    print("\nChecking source files:")
    all_good = True

    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - REQUIRED")
            all_good = False

    return all_good


def main():
    """Main verification function."""
    print("🔍 PPL Meta Mini - Cython Build Verification")
    print("=" * 50)

    checks = [
        ("Python Version", check_python_version),
        ("Required Modules", check_required_modules),
        ("Docker", check_docker),
        ("Source Files", check_source_files),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        result = check_func()
        results.append((name, result))

    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY:")

    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False

    if all_passed:
        print(f"\n🎉 All checks passed! Ready to build Cython Docker image.")
        print("\nNext steps:")
        print("1. Run: ./build_cython_docker.sh")
        print("2. Or: docker build -f Dockerfile.cython -t ppl-meta-mini:cython .")
        return True
    else:
        print(f"\n❌ Some checks failed. Please fix the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
