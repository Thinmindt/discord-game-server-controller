"""Test Project Zomboid batch file modification logic."""

import pathlib
import tempfile

import pytest

from src.project_zomboid_manager import ProjectZomboidServerManager


def test_batch_file_default_servername():
    """Test that default server name uses original batch file."""
    # Create a temporary directory and batch file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)
        batch_file = temp_path / "StartServer64.bat"

        # Create a mock batch file
        batch_content = """@echo off
cd /d "%~dp0"
SET PZ_CLASSPATH=java/all.jar
".\\jre64\\bin\\java.exe" -Xms4g -Xmx4g -cp %PZ_CLASSPATH% zombie.network.GameServer
PAUSE
"""
        batch_file.write_text(batch_content)

        # Create manager with default server name
        manager = ProjectZomboidServerManager(
            server_path=temp_path,
            steam_cmd_path=pathlib.Path("steamcmd"),
            server_name="servertest",  # default name
        )

        # Should return original batch file
        result = manager._modify_batch_file(batch_file)
        assert result == batch_file
        assert result.exists()
        # Should not create any custom batch files
        custom_batch = temp_path / "StartServer64_servertest.bat"
        assert not custom_batch.exists()


def test_batch_file_custom_servername():
    """Test that custom server name creates modified batch file."""
    # Create a temporary directory and batch file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)
        batch_file = temp_path / "StartServer64.bat"

        # Create a mock batch file
        batch_content = """@echo off
cd /d "%~dp0"
SET PZ_CLASSPATH=java/all.jar
".\\jre64\\bin\\java.exe" -Xms4g -Xmx4g -cp %PZ_CLASSPATH% zombie.network.GameServer
PAUSE
"""
        batch_file.write_text(batch_content)

        # Create manager with custom server name
        manager = ProjectZomboidServerManager(
            server_path=temp_path,
            steam_cmd_path=pathlib.Path("steamcmd"),
            server_name="MyCustomServer",
        )

        # Should create and return custom batch file
        result = manager._modify_batch_file(batch_file)
        custom_batch = temp_path / "StartServer64_MyCustomServer.bat"
        assert result == custom_batch
        assert custom_batch.exists()

        # Check that the custom batch file has the server name inserted
        modified_content = custom_batch.read_text()
        assert "zombie.network.GameServer -servername MyCustomServer" in modified_content
        # Ensure original content structure is preserved
        assert "@echo off" in modified_content
        assert "SET PZ_CLASSPATH=java/all.jar" in modified_content
        assert "PAUSE" in modified_content


def test_batch_file_regenerates_existing_custom():
    """Test that an existing custom batch file is always regenerated from the original."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)
        batch_file = temp_path / "StartServer64.bat"
        custom_batch = temp_path / "StartServer64_MyServer.bat"

        batch_content = """@echo off
cd /d "%~dp0"
SET PZ_CLASSPATH=java/all.jar
".\\jre64\\bin\\java.exe" -Xms4g -Xmx4g -cp %PZ_CLASSPATH% zombie.network.GameServer
PAUSE
"""
        batch_file.write_text(batch_content)
        custom_batch.write_text("stale content")

        manager = ProjectZomboidServerManager(
            server_path=temp_path,
            steam_cmd_path=pathlib.Path("steamcmd"),
            server_name="MyServer",
        )

        result = manager._modify_batch_file(batch_file)
        assert result == custom_batch
        regenerated = custom_batch.read_text()
        assert "zombie.network.GameServer -servername MyServer" in regenerated
        assert "stale content" not in regenerated


def test_batch_file_missing_gameserver():
    """Test error when GameServer pattern not found."""
    # Create a temporary directory and batch file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)
        batch_file = temp_path / "StartServer64.bat"

        # Create a batch file without GameServer pattern
        batch_content = """@echo off
cd /d "%~dp0"
echo "This is not a valid PZ server batch file"
PAUSE
"""
        batch_file.write_text(batch_content)

        # Create manager
        manager = ProjectZomboidServerManager(
            server_path=temp_path,
            steam_cmd_path=pathlib.Path("steamcmd"),
            server_name="MyServer",
        )

        # Should raise error
        from src.game_server_interface import ServerControlError

        with pytest.raises(ServerControlError, match="Could not find 'zombie.network.GameServer'"):
            manager._modify_batch_file(batch_file)
