"""
Temporary Storage Manager for PPL Meta Mini - Upgrade 2 Implementation
Handles temporary file and directory management with automatic cleanup.
"""

import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional, List


class TempStorageManager:
    """
    Manages temporary storage for camera recordings and processing.
    Provides automatic cleanup and organized temporary file management.
    """

    def __init__(self, base_temp_dir: Optional[str] = None):
        """
        Initialize the Temporary Storage Manager.
        
        Args:
            base_temp_dir: Base directory for temporary storage. 
                          Defaults to system temp + 'ppl-mini-camera'
        """
        self.logger = logging.getLogger(__name__)
        
        # Set up base temporary directory
        if base_temp_dir:
            self.base_temp_dir = Path(base_temp_dir)
        else:
            self.base_temp_dir = Path(tempfile.gettempdir()) / "ppl-mini-camera"
        
        # Ensure base directory exists
        self.base_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Track created files and directories for cleanup
        self.created_files = set()
        self.created_directories = set()
        
        self.logger.info(f"TempStorageManager initialized: {self.base_temp_dir}")

    def create_temp_directory(self, prefix: str = "recording_") -> str:
        """
        Create a temporary directory for camera operations.
        
        Args:
            prefix: Prefix for the directory name
            
        Returns:
            str: Absolute path to the created directory
        """
        timestamp = str(int(time.time()))
        dir_name = f"{prefix}{timestamp}"
        temp_dir = self.base_temp_dir / dir_name
        
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.created_directories.add(str(temp_dir))
            
            self.logger.info(f"📁 Created temp directory: {temp_dir}")
            return str(temp_dir)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create temp directory: {e}")
            raise RuntimeError(f"Failed to create temp directory: {e}")

    def generate_temp_filename(self, 
                              extension: str = ".mp4", 
                              prefix: str = "recording_") -> str:
        """
        Generate a unique temporary filename.
        
        Args:
            extension: File extension (include the dot)
            prefix: Prefix for the filename
            
        Returns:
            str: Absolute path to the temp file
        """
        timestamp = str(int(time.time() * 1000))  # Include milliseconds
        filename = f"{prefix}{timestamp}{extension}"
        temp_file_path = self.base_temp_dir / filename
        
        # Track the file for cleanup
        self.created_files.add(str(temp_file_path))
        
        self.logger.debug(f"📄 Generated temp filename: {temp_file_path}")
        return str(temp_file_path)

    def cleanup_temp_file(self, file_path: str) -> bool:
        """
        Clean up a specific temporary file.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        try:
            file_path_obj = Path(file_path)
            
            if file_path_obj.exists():
                file_path_obj.unlink()
                self.logger.info(f"🗑️ Cleaned up temp file: {file_path}")
            
            # Remove from tracking
            self.created_files.discard(file_path)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to cleanup file {file_path}: {e}")
            return False

    def cleanup_temp_directory(self, directory_path: str) -> bool:
        """
        Clean up a specific temporary directory and its contents.
        
        Args:
            directory_path: Path to the directory to delete
            
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        try:
            dir_path_obj = Path(directory_path)
            
            if dir_path_obj.exists() and dir_path_obj.is_dir():
                shutil.rmtree(str(dir_path_obj))
                self.logger.info(f"🗑️ Cleaned up temp directory: {directory_path}")
            
            # Remove from tracking
            self.created_directories.discard(directory_path)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to cleanup directory {directory_path}: {e}")
            return False

    def cleanup_all_temp_files(self) -> int:
        """
        Clean up all tracked temporary files.
        
        Returns:
            int: Number of files successfully cleaned up
        """
        cleaned_count = 0
        files_to_cleanup = list(self.created_files)  # Create copy to avoid modification during iteration
        
        for file_path in files_to_cleanup:
            if self.cleanup_temp_file(file_path):
                cleaned_count += 1
        
        self.logger.info(f"🧹 Cleaned up {cleaned_count} temporary files")
        return cleaned_count

    def cleanup_all_temp_directories(self) -> int:
        """
        Clean up all tracked temporary directories.
        
        Returns:
            int: Number of directories successfully cleaned up
        """
        cleaned_count = 0
        dirs_to_cleanup = list(self.created_directories)  # Create copy
        
        for dir_path in dirs_to_cleanup:
            if self.cleanup_temp_directory(dir_path):
                cleaned_count += 1
        
        self.logger.info(f"🧹 Cleaned up {cleaned_count} temporary directories")
        return cleaned_count

    def cleanup_all(self) -> dict:
        """
        Clean up all temporary files and directories.
        
        Returns:
            dict: Cleanup statistics
        """
        self.logger.info("🧹 Starting complete temporary storage cleanup...")
        
        files_cleaned = self.cleanup_all_temp_files()
        dirs_cleaned = self.cleanup_all_temp_directories()
        
        cleanup_stats = {
            "files_cleaned": files_cleaned,
            "directories_cleaned": dirs_cleaned,
            "total_items_cleaned": files_cleaned + dirs_cleaned
        }
        
        self.logger.info(f"✅ Cleanup complete: {cleanup_stats}")
        return cleanup_stats

    def get_temp_directory_info(self) -> dict:
        """
        Get information about the temporary storage.
        
        Returns:
            dict: Storage information including size and file counts
        """
        try:
            total_size = 0
            file_count = 0
            dir_count = 0
            
            if self.base_temp_dir.exists():
                for item in self.base_temp_dir.rglob("*"):
                    if item.is_file():
                        total_size += item.stat().st_size
                        file_count += 1
                    elif item.is_dir():
                        dir_count += 1
            
            return {
                "base_directory": str(self.base_temp_dir),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "directory_count": dir_count,
                "tracked_files": len(self.created_files),
                "tracked_directories": len(self.created_directories)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get storage info: {e}")
            return {
                "error": str(e),
                "base_directory": str(self.base_temp_dir)
            }

    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than specified age.
        
        Args:
            max_age_hours: Maximum age of files to keep in hours
            
        Returns:
            int: Number of old files cleaned up
        """
        self.logger.info(f"🧹 Cleaning up files older than {max_age_hours} hours...")
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        
        try:
            if not self.base_temp_dir.exists():
                return 0
            
            for item in self.base_temp_dir.rglob("*"):
                if item.is_file():
                    file_age = current_time - item.stat().st_mtime
                    
                    if file_age > max_age_seconds:
                        try:
                            item.unlink()
                            cleaned_count += 1
                            self.logger.debug(f"🗑️ Removed old file: {item}")
                        except Exception as e:
                            self.logger.warning(f"Failed to remove old file {item}: {e}")
            
            self.logger.info(f"✅ Cleaned up {cleaned_count} old files")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"❌ Error during old file cleanup: {e}")
            return cleaned_count

    def ensure_storage_space(self, required_mb: int = 100) -> bool:
        """
        Ensure there's enough storage space available.
        
        Args:
            required_mb: Required space in megabytes
            
        Returns:
            bool: True if enough space is available
        """
        try:
            statvfs = os.statvfs(str(self.base_temp_dir))
            available_bytes = statvfs.f_frsize * statvfs.f_bavail
            available_mb = available_bytes / (1024 * 1024)
            
            if available_mb >= required_mb:
                self.logger.debug(f"✅ Sufficient storage: {available_mb:.1f}MB available")
                return True
            else:
                self.logger.warning(
                    f"⚠️ Insufficient storage: {available_mb:.1f}MB available, "
                    f"{required_mb}MB required"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to check storage space: {e}")
            return False

    def get_tracked_files(self) -> List[str]:
        """
        Get list of all tracked temporary files.
        
        Returns:
            List[str]: List of tracked file paths
        """
        return list(self.created_files)

    def get_tracked_directories(self) -> List[str]:
        """
        Get list of all tracked temporary directories.
        
        Returns:
            List[str]: List of tracked directory paths
        """
        return list(self.created_directories)

    def __del__(self):
        """Cleanup on object destruction."""
        try:
            # Don't automatically cleanup on destruction to avoid data loss
            # User should explicitly call cleanup methods
            pass
        except Exception:
            pass  # Ignore errors during destruction