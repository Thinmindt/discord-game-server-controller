"""Tests for the BackupUtility class in backup_manager.py."""

import pathlib
import tempfile
from datetime import datetime, timedelta


from src.backup_manager import BackupResult, BackupUtility


class TestBackupResult:
    """Tests for the BackupResult dataclass."""

    def test_backup_result_success(self):
        """Test creating a successful BackupResult."""
        result = BackupResult(
            success=True,
            backup_path=pathlib.Path("/backups/server_20260103_120000"),
            message="Successfully backed up 3 items",
            files_backed_up=["config", "saves (folder)", "database"],
        )

        assert result.success is True
        assert result.backup_path == pathlib.Path("/backups/server_20260103_120000")
        assert result.message == "Successfully backed up 3 items"
        assert len(result.files_backed_up) == 3

    def test_backup_result_failure(self):
        """Test creating a failed BackupResult."""
        result = BackupResult(
            success=False,
            backup_path=None,
            message="Failed to create backup directory",
            files_backed_up=[],
        )

        assert result.success is False
        assert result.backup_path is None
        assert "Failed" in result.message
        assert len(result.files_backed_up) == 0


class TestBackupUtility:
    """Tests for the BackupUtility class."""

    def test_initialization(self):
        """Test BackupUtility initialization."""
        backup_path = pathlib.Path("/backups")
        utility = BackupUtility(backup_path, "TestServer")

        assert utility.backup_base_path == backup_path
        assert utility.identifier == "TestServer"

    def test_create_backup_single_file(self):
        """Test backing up a single file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            source_path = temp_path / "source"
            source_path.mkdir()

            # Create a test file
            test_file = source_path / "config.ini"
            test_file.write_text("test config content")

            utility = BackupUtility(backup_path, "TestServer")
            result = utility.create_backup(
                paths_to_backup={"config": test_file},
            )

            assert result.success is True
            assert result.backup_path is not None
            assert result.backup_path.exists()
            assert "config" in result.files_backed_up
            assert (result.backup_path / "config.ini").exists()
            assert (result.backup_path / "config.ini").read_text() == "test config content"

    def test_create_backup_directory(self):
        """Test backing up a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            source_path = temp_path / "source"
            source_path.mkdir()

            # Create a test directory with files
            test_dir = source_path / "saves"
            test_dir.mkdir()
            (test_dir / "world.dat").write_text("world data")
            (test_dir / "players.dat").write_text("player data")

            utility = BackupUtility(backup_path, "TestServer")
            result = utility.create_backup(
                paths_to_backup={"saves_folder": test_dir},
            )

            assert result.success is True
            assert result.backup_path is not None
            assert "saves_folder (folder)" in result.files_backed_up
            assert (result.backup_path / "saves").exists()
            assert (result.backup_path / "saves" / "world.dat").read_text() == "world data"

    def test_create_backup_multiple_items(self):
        """Test backing up multiple files and directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            source_path = temp_path / "source"
            source_path.mkdir()

            # Create test files
            config_file = source_path / "server.ini"
            config_file.write_text("server config")

            database_file = source_path / "players.db"
            database_file.write_text("player database")

            saves_dir = source_path / "saves"
            saves_dir.mkdir()
            (saves_dir / "map.dat").write_text("map data")

            utility = BackupUtility(backup_path, "TestServer")
            result = utility.create_backup(
                paths_to_backup={
                    "config": config_file,
                    "database": database_file,
                    "saves": saves_dir,
                },
            )

            assert result.success is True
            assert len(result.files_backed_up) == 3
            assert "config" in result.files_backed_up
            assert "database" in result.files_backed_up
            assert "saves (folder)" in result.files_backed_up

    def test_create_backup_with_friendly_names(self):
        """Test that friendly names are used in progress callbacks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            source_path = temp_path / "source"
            source_path.mkdir()

            test_file = source_path / "config.ini"
            test_file.write_text("config")

            progress_messages = []

            def progress_callback(message: str) -> None:
                progress_messages.append(message)

            utility = BackupUtility(backup_path, "TestServer")
            utility.create_backup(
                paths_to_backup={"config_file": test_file},
                friendly_names={"config_file": "server configuration"},
                progress_callback=progress_callback,
            )

            assert any("server configuration" in msg for msg in progress_messages)

    def test_create_backup_missing_file_skipped(self):
        """Test that missing files are gracefully skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            source_path = temp_path / "source"
            source_path.mkdir()

            # Create one file, but reference another that doesn't exist
            existing_file = source_path / "config.ini"
            existing_file.write_text("config")

            missing_file = source_path / "optional.ini"

            utility = BackupUtility(backup_path, "TestServer")
            result = utility.create_backup(
                paths_to_backup={
                    "config": existing_file,
                    "optional": missing_file,
                },
            )

            assert result.success is True
            assert "config" in result.files_backed_up
            assert "optional" not in result.files_backed_up

    def test_create_backup_no_files_found(self):
        """Test backup fails when no files exist to backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"

            # Reference files that don't exist
            missing_file1 = temp_path / "missing1.ini"
            missing_file2 = temp_path / "missing2.ini"

            utility = BackupUtility(backup_path, "TestServer")
            result = utility.create_backup(
                paths_to_backup={
                    "file1": missing_file1,
                    "file2": missing_file2,
                },
            )

            assert result.success is False
            assert "No files found" in result.message
            assert len(result.files_backed_up) == 0

    def test_create_backup_timestamp_format(self):
        """Test that backup directory has correct timestamp format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            source_path = temp_path / "source"
            source_path.mkdir()

            test_file = source_path / "config.ini"
            test_file.write_text("config")

            utility = BackupUtility(backup_path, "MyServer")
            result = utility.create_backup(
                paths_to_backup={"config": test_file},
            )

            assert result.backup_path is not None
            # Check folder name format: MyServer_YYYYMMDD_HHMMSS
            folder_name = result.backup_path.name
            assert folder_name.startswith("MyServer_")

            # Extract and validate timestamp
            timestamp_str = folder_name[len("MyServer_") :]
            # Should not raise ValueError if format is correct
            datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

    def test_cleanup_old_backups(self):
        """Test that old backups are removed correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            backup_path.mkdir()

            # Create 8 backup folders with different timestamps
            base_time = datetime(2026, 1, 1, 12, 0, 0)
            for i in range(8):
                timestamp = base_time + timedelta(hours=i)
                folder_name = f"TestServer_{timestamp.strftime('%Y%m%d_%H%M%S')}"
                (backup_path / folder_name).mkdir()
                # Add a file so we can verify deletion
                (backup_path / folder_name / "data.txt").write_text(f"backup {i}")

            utility = BackupUtility(backup_path, "TestServer")
            utility.cleanup_old_backups(max_backups=3)

            # Should have exactly 3 backups remaining
            remaining = list(backup_path.iterdir())
            assert len(remaining) == 3

            # The 3 newest backups should remain (hours 5, 6, 7)
            remaining_names = [f.name for f in remaining]
            assert "TestServer_20260101_170000" in remaining_names  # hour 5
            assert "TestServer_20260101_180000" in remaining_names  # hour 6
            assert "TestServer_20260101_190000" in remaining_names  # hour 7

    def test_cleanup_old_backups_fewer_than_max(self):
        """Test cleanup does nothing when fewer backups than max."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            backup_path.mkdir()

            # Create only 2 backup folders
            (backup_path / "TestServer_20260101_120000").mkdir()
            (backup_path / "TestServer_20260101_130000").mkdir()

            utility = BackupUtility(backup_path, "TestServer")
            utility.cleanup_old_backups(max_backups=6)

            # Both should remain
            remaining = list(backup_path.iterdir())
            assert len(remaining) == 2

    def test_cleanup_old_backups_progress_callback(self):
        """Test that cleanup sends progress messages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            backup_path.mkdir()

            # Create 4 backup folders
            base_time = datetime(2026, 1, 1, 12, 0, 0)
            for i in range(4):
                timestamp = base_time + timedelta(hours=i)
                folder_name = f"TestServer_{timestamp.strftime('%Y%m%d_%H%M%S')}"
                (backup_path / folder_name).mkdir()

            progress_messages = []

            def progress_callback(message: str) -> None:
                progress_messages.append(message)

            utility = BackupUtility(backup_path, "TestServer")
            utility.cleanup_old_backups(max_backups=2, progress_callback=progress_callback)

            # Should have 2 progress messages for removing 2 old backups
            assert len(progress_messages) == 2
            assert all("Removing old backup" in msg for msg in progress_messages)

    def test_cleanup_ignores_other_server_backups(self):
        """Test that cleanup only affects backups for this identifier."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            backup_path.mkdir()

            # Create backups for two different servers
            (backup_path / "ServerA_20260101_120000").mkdir()
            (backup_path / "ServerA_20260101_130000").mkdir()
            (backup_path / "ServerA_20260101_140000").mkdir()
            (backup_path / "ServerB_20260101_120000").mkdir()
            (backup_path / "ServerB_20260101_130000").mkdir()

            utility = BackupUtility(backup_path, "ServerA")
            utility.cleanup_old_backups(max_backups=1)

            # ServerA should have 1 backup, ServerB should be untouched
            remaining = list(backup_path.iterdir())
            remaining_names = [f.name for f in remaining]
            assert len(remaining) == 3
            assert sum(1 for n in remaining_names if n.startswith("ServerA_")) == 1
            assert sum(1 for n in remaining_names if n.startswith("ServerB_")) == 2

    def test_get_recent_backups(self):
        """Test getting recent backup timestamps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            backup_path.mkdir()

            # Create 5 backup folders
            (backup_path / "TestServer_20260101_100000").mkdir()
            (backup_path / "TestServer_20260101_110000").mkdir()
            (backup_path / "TestServer_20260101_120000").mkdir()
            (backup_path / "TestServer_20260101_130000").mkdir()
            (backup_path / "TestServer_20260101_140000").mkdir()

            utility = BackupUtility(backup_path, "TestServer")
            recent = utility.get_recent_backups(count=3)

            assert len(recent) == 3
            # Should be in descending order (newest first)
            assert "Jan 01, 2026 at 02:00 PM" in recent[0]
            assert "Jan 01, 2026 at 01:00 PM" in recent[1]
            assert "Jan 01, 2026 at 12:00 PM" in recent[2]

    def test_get_recent_backups_fewer_than_count(self):
        """Test get_recent_backups when fewer backups exist than requested."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            backup_path.mkdir()

            # Create only 2 backup folders
            (backup_path / "TestServer_20260101_120000").mkdir()
            (backup_path / "TestServer_20260101_130000").mkdir()

            utility = BackupUtility(backup_path, "TestServer")
            recent = utility.get_recent_backups(count=5)

            assert len(recent) == 2

    def test_get_recent_backups_no_backups(self):
        """Test get_recent_backups when no backups exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            backup_path.mkdir()

            utility = BackupUtility(backup_path, "TestServer")
            recent = utility.get_recent_backups(count=3)

            assert len(recent) == 0

    def test_get_recent_backups_nonexistent_directory(self):
        """Test get_recent_backups when backup directory doesn't exist."""
        backup_path = pathlib.Path("/nonexistent/path")
        utility = BackupUtility(backup_path, "TestServer")
        recent = utility.get_recent_backups(count=3)

        assert len(recent) == 0

    def test_get_backup_folders_ignores_invalid_format(self):
        """Test that folders with invalid timestamp format are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            backup_path = temp_path / "backups"
            backup_path.mkdir()

            # Create valid and invalid folder names
            (backup_path / "TestServer_20260101_120000").mkdir()  # Valid
            (backup_path / "TestServer_invalid").mkdir()  # Invalid
            (backup_path / "TestServer_2026-01-01").mkdir()  # Wrong format
            (backup_path / "OtherServer_20260101_120000").mkdir()  # Different server

            utility = BackupUtility(backup_path, "TestServer")
            folders = utility._get_backup_folders()

            # Should only find the one valid folder
            assert len(folders) == 1
            assert folders[0][0] == datetime(2026, 1, 1, 12, 0, 0)

    def test_cleanup_nonexistent_directory(self):
        """Test cleanup gracefully handles nonexistent backup directory."""
        backup_path = pathlib.Path("/nonexistent/path")
        utility = BackupUtility(backup_path, "TestServer")

        # Should not raise any exceptions
        utility.cleanup_old_backups(max_backups=3)
