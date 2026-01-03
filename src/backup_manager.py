"""
Backup utility for game server data.

This module provides a reusable BackupUtility class that can be used by any
game server manager to create timestamped backups of server data.
"""

import logging
import pathlib
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class BackupResult:
    """Result of a backup operation."""

    success: bool
    backup_path: Optional[pathlib.Path]
    message: str
    files_backed_up: List[str]


class BackupUtility:
    """
    Utility class for creating and managing server backups.

    This class handles the generic backup operations that can be shared
    across different game server types.
    """

    def __init__(self, backup_base_path: pathlib.Path, identifier: str):
        """
        Initialize the backup utility.

        Args:
            backup_base_path: Base directory for all backups
            identifier: Unique name for this backup set (e.g., server name)
        """
        self.backup_base_path = backup_base_path
        self.identifier = identifier

    def create_backup(
        self,
        paths_to_backup: Dict[str, pathlib.Path],
        friendly_names: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> BackupResult:
        """
        Create a backup of the specified paths.

        Args:
            paths_to_backup: Dictionary mapping item names to source paths
            friendly_names: Optional dictionary mapping item names to display names
            progress_callback: Optional callback function for progress messages

        Returns:
            BackupResult with success status, backup path, and list of files backed up
        """
        # Create backup directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_base_path / f"{self.identifier}_{timestamp}"

        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return BackupResult(
                success=False,
                backup_path=None,
                message=f"Failed to create backup directory: {e}",
                files_backed_up=[],
            )

        friendly_names = friendly_names or {}
        files_backed_up: List[str] = []
        errors: List[str] = []

        for name, source_path in paths_to_backup.items():
            try:
                friendly_name = friendly_names.get(name, name)
                if source_path.exists():
                    if progress_callback:
                        progress_callback(f"📦 Backing up {friendly_name}...")
                    logging.debug(f"Backing up {name} from {source_path}...")

                    if source_path.is_dir():
                        # Copy entire directory
                        dest_path = backup_dir / source_path.name
                        shutil.copytree(source_path, dest_path)
                        files_backed_up.append(f"{name} (folder)")
                    else:
                        # Copy single file
                        dest_path = backup_dir / source_path.name
                        shutil.copy2(source_path, dest_path)
                        files_backed_up.append(name)
                else:
                    # File doesn't exist - this is okay for some optional files
                    logging.debug(f"Skipping {name}: path does not exist ({source_path})")
            except (OSError, shutil.Error) as e:
                errors.append(f"{name}: {e}")

        if not files_backed_up:
            return BackupResult(
                success=False,
                backup_path=backup_dir,
                message=f"No files found to backup for '{self.identifier}'.",
                files_backed_up=[],
            )

        if errors:
            return BackupResult(
                success=False,
                backup_path=backup_dir,
                message=f"Backup completed with errors: {'; '.join(errors)}",
                files_backed_up=files_backed_up,
            )

        return BackupResult(
            success=True,
            backup_path=backup_dir,
            message=f"Successfully backed up {len(files_backed_up)} items",
            files_backed_up=files_backed_up,
        )

    def cleanup_old_backups(
        self,
        max_backups: int = 6,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Remove old backups, keeping only the most recent ones.

        Args:
            max_backups: Maximum number of backups to keep
            progress_callback: Optional callback function for progress messages
        """
        if not self.backup_base_path.exists():
            return

        # Find all backup folders for this identifier
        backup_folders = self._get_backup_folders()

        # Remove backups beyond the max count
        if len(backup_folders) > max_backups:
            folders_to_remove = backup_folders[max_backups:]
            for timestamp, folder in folders_to_remove:
                try:
                    if progress_callback:
                        friendly_date = timestamp.strftime("%b %d, %Y at %I:%M %p")
                        progress_callback(f"🗑️ Removing old backup from {friendly_date}...")
                    shutil.rmtree(folder)
                    logging.debug(f"Removed old backup: {folder}")
                except (OSError, shutil.Error) as e:
                    logging.warning(f"Failed to remove old backup {folder}: {e}")

    def get_recent_backups(self, count: int = 3) -> List[str]:
        """
        Get the most recent backup timestamps as friendly formatted strings.

        Args:
            count: Number of recent backups to return

        Returns:
            List of formatted timestamp strings for recent backups
        """
        backup_folders = self._get_backup_folders()
        recent = backup_folders[:count]

        # Format timestamps as friendly strings
        formatted = []
        for timestamp, _folder in recent:
            formatted.append(timestamp.strftime("%b %d, %Y at %I:%M %p"))

        return formatted

    def _get_backup_folders(self) -> List[Tuple[datetime, pathlib.Path]]:
        """
        Get all backup folders for this identifier, sorted by timestamp descending.

        Returns:
            List of (timestamp, folder_path) tuples, newest first
        """
        if not self.backup_base_path.exists():
            return []

        prefix = f"{self.identifier}_"
        backup_folders = []

        for folder in self.backup_base_path.iterdir():
            if folder.is_dir() and folder.name.startswith(prefix):
                # Extract timestamp from folder name
                timestamp_str = folder.name[len(prefix) :]
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    backup_folders.append((timestamp, folder))
                except ValueError:
                    # Skip folders that don't match expected format
                    continue

        # Sort by timestamp descending (newest first)
        backup_folders.sort(key=lambda x: x[0], reverse=True)
        return backup_folders
