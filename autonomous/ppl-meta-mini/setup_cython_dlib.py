"""
Setup script for Cython compilation of PPL Meta Mini with dlib support
"""

import os
from pathlib import Path

from Cython.Build import cythonize
from setuptools import Extension, find_packages, setup

# Get the source directory
src_dir = Path("src")

# Find Python files to compile - exclude FastAPI-specific files
python_files = []
# Exclude patterns - files that contain FastAPI objects incompatible with Cython
exclude_patterns = [
    "main.py",  # Contains FastAPI app
    "api/",  # API endpoints with Query objects
]

for root, dirs, files in os.walk(src_dir):
    # Skip __pycache__ directories
    dirs[:] = [d for d in dirs if d != "__pycache__"]

    for file in files:
        if file.endswith(".py") and not file.startswith("__"):
            rel_path = os.path.relpath(os.path.join(root, file))

            # Check if file should be excluded
            should_exclude = any(pattern in rel_path for pattern in exclude_patterns)

            if not should_exclude:
                python_files.append(rel_path)

print(f"Found {len(python_files)} Python files to compile:")
for file in python_files:
    print(f"  - {file}")

# Create extensions for each Python file
extensions = []
for py_file in python_files:
    # Convert file path to module name
    module_name = py_file.replace(os.sep, ".").replace(".py", "")

    # Create extension
    ext = Extension(
        name=module_name,
        sources=[py_file],
        include_dirs=[],
        libraries=[],
        library_dirs=[],
        define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
    )
    extensions.append(ext)

# Compiler directives for optimization
compiler_directives = {
    "language_level": 3,
    "boundscheck": False,
    "wraparound": False,
    "initializedcheck": False,
    "cdivision": True,
    "embedsignature": True,
}

# Setup configuration
setup(
    name="ppl-meta-mini",
    version="1.1.0",
    description=("PPL Meta Mini - Standalone Face Analytics Service (Cython + dlib)"),
    author="PPL Meta Team",
    packages=find_packages(),
    ext_modules=cythonize(
        extensions,
        compiler_directives=compiler_directives,
        build_dir="build",
        annotate=False,  # Set to True for HTML annotation files
    ),
    zip_safe=False,
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.5.0",
        "pandas>=2.1.4",
        "plotly>=5.17.0",
        "python-multipart>=0.0.6",
        "opencv-python>=4.8.1.78",
        "dlib>=19.24.2",  # Re-enabled with proper CMake setup
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
