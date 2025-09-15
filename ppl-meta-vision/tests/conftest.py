#!/usr/bin/env python3
"""
PPL Meta Vision Service - Test Configuration

Test configuration and setup for the PPL Meta Vision Service unit tests.
"""

import sys
from pathlib import Path

# Setup paths for imports
current_dir = Path(__file__).parent
src_dir = current_dir / ".." / "src"
sys.path.insert(0, str(src_dir.resolve()))

# Add parent directory for shared modules
parent_dir = current_dir / ".." / ".." / ".."
sys.path.insert(0, str(parent_dir.resolve()))

# Test configuration
TEST_CONFIG = {
    "database": {"test_db_name": "test_ppl_meta_vision", "use_memory_db": True},
    "session": {"test_timeout": 30, "cleanup_after_test": True},
    "performance": {
        "session_creation_max_ms": 50,
        "face_storage_max_ms": 10,
        "analytics_query_max_ms": 100,
    },
}
