"""
PPL Meta Vision Service - Database Module
Handles database operations and migrations for person objects functionality.
"""

import os
import sys

# Import migration components
from .person_objects_migrations import PersonObjectsMigration

# Add parent directory to import VisionDatabase from main database.py
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import VisionDatabase from parent directory
try:
    from database import VisionDatabase as _VisionDatabase

    VisionDatabase = _VisionDatabase
except ImportError:
    VisionDatabase = None

__all__ = ["PersonObjectsMigration", "VisionDatabase"]
