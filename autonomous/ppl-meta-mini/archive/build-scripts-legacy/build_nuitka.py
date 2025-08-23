#!/usr/bin/env python3
"""
Nuitka build script for PPL Meta Mini service
"""

import os
import subprocess
import sys
from pathlib import Path


def check_packages():
    """Check if required packages are installed"""
    required_packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "opencv-python": "cv2",
        "deepface": "deepface",
        "numpy": "numpy",
        "pillow": "PIL",
        "tensorflow": "tensorflow",
    }

    missing_packages = []
    available_packages = []

    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            available_packages.append(package_name)
            print(f"✅ {package_name} found")
        except ImportError:
            missing_packages.append(package_name)
            print(f"❌ {package_name} missing")

    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False, available_packages

    return True, available_packages


def main():
    """Build PPL Meta Mini with Nuitka"""

    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    src_dir = script_dir / "src"

    # Change to the src directory
    os.chdir(src_dir)

    print("🏗️  Building PPL Meta Mini with Nuitka...")
    print(f"📁 Working directory: {src_dir}")

    # Check if packages are installed
    packages_ok, available_packages = check_packages()
    if not packages_ok:
        print("\n💡 Try building anyway with available packages? (y/n): ", end="")
        response = input().lower()
        if response != "y":
            sys.exit(1)

    # Basic Nuitka command with only essential packages
    nuitka_cmd = [
        "python",
        "-m",
        "nuitka",
        "--standalone",
        "--follow-imports",
        # Core application packages
        "--include-package=api",
        "--include-package=services",
        # Essential dependencies
        "--include-package=fastapi",
        "--include-package=uvicorn",
        "--include-package=pydantic",
        # Only include if available
        "--output-dir=../dist",
        "--output-filename=ppl-meta-mini",
        "main.py",
    ]

    # Add optional packages if available
    optional_includes = {
        "opencv-python": "--include-package=cv2",
        "numpy": "--include-package=numpy",
        "pillow": "--include-package=PIL",
        "deepface": "--include-package=deepface",
        "tensorflow": "--include-package=tensorflow",
    }

    for package, include_flag in optional_includes.items():
        if package in available_packages:
            nuitka_cmd.insert(-1, include_flag)

    try:
        print("🔨 Running Nuitka compilation...")
        print(" ".join(nuitka_cmd))

        result = subprocess.run(nuitka_cmd, check=True, capture_output=True, text=True)
        print("✅ Nuitka compilation successful!")

        # Check if the executable was created
        dist_dir = script_dir / "dist"
        executable_path = dist_dir / "ppl-meta-mini.dist" / "ppl-meta-mini"

        if executable_path.exists():
            print(f"✅ Executable created at: {executable_path}")
            print(f"📦 Distribution directory: {dist_dir / 'ppl-meta-mini.dist'}")

            # Make executable
            os.chmod(executable_path, 0o755)
            print("✅ Executable permissions set")

        else:
            print("⚠️  Executable not found at expected location")
            print("Checking dist directory contents...")
            if dist_dir.exists():
                for item in dist_dir.iterdir():
                    print(f"  Found: {item}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Nuitka compilation failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)

        sys.exit(1)
    except FileNotFoundError:
        print("❌ Nuitka not found. Please install with: pip install nuitka")
        sys.exit(1)


if __name__ == "__main__":
    main()
