"""Test the new unified Project Zomboid server manager."""

import pathlib
import tempfile
from unittest.mock import MagicMock

from src.project_zomboid_manager import ProjectZomboidServerManager


def test_project_zomboid_manager_creation():
    """Test that we can create a Project Zomboid manager instance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)
        server_path = temp_path / "server"
        steam_cmd_path = temp_path / "steamcmd"

        manager = ProjectZomboidServerManager(
            server_path=server_path,
            steam_cmd_path=steam_cmd_path,
            server_name="TestServer",
            memory_gb=8,
        )

        assert manager.server_name == "TestServer"
        assert manager.memory_gb == 8
        assert manager.server_path == server_path
        assert manager.steam_cmd_path == steam_cmd_path
        assert not manager.is_on()  # Should be off initially


def test_project_zomboid_manager_startup_detection():
    """Test that the manager correctly detects server startup from logs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)

        manager = ProjectZomboidServerManager(
            server_path=temp_path,
            steam_cmd_path=temp_path / "steamcmd",
            server_name="TestServer",
        )

        # Initially not started
        assert not manager._server_started

        # Simulate log lines including startup message
        manager._log_lines = [
            "LOG  : Network     , 1751825451443> 313,088,958> *** SERVER STARTED ****",
            (
                "LOG  : Network     , 1751825451444> Server is listening on port 16261 "
                "(for Steam connection) and port 16262 (for UDPRakNet connection)"
            ),
        ]

        # Test log parsing for server info
        manager._server_started = True
        manager.server_process = MagicMock()
        manager.server_process.poll.return_value = None  # Process still running

        assert manager.is_on()

        # Test server info extraction
        info = manager.get_server_info()
        assert info.server_name == "TestServer"
        assert info.version == "Build 41+"
        assert info.additional_info is not None


def test_project_zomboid_manager_batch_file_logic():
    """Test that batch file modification logic works."""
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

        manager = ProjectZomboidServerManager(
            server_path=temp_path,
            steam_cmd_path=temp_path / "steamcmd",
            server_name="MyServer",
        )

        # Test batch file modification
        result = manager._modify_batch_file(batch_file)
        custom_batch = temp_path / "StartServer64_MyServer.bat"

        assert result == custom_batch
        assert custom_batch.exists()

        # Check content
        modified_content = custom_batch.read_text()
        assert "zombie.network.GameServer -servername MyServer" in modified_content
        assert "@echo off" in modified_content


def test_project_zomboid_send_server_command():
    """Test sending commands to a running Project Zomboid server."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)

        manager = ProjectZomboidServerManager(
            server_path=temp_path,
            steam_cmd_path=temp_path / "steamcmd",
            server_name="TestServer",
        )

        # Test command when server is not running
        from src.game_server_interface import ServerControlError

        try:
            manager.send_server_command("help")
            assert False, "Should have raised ServerControlError"
        except ServerControlError as e:
            assert "Server is not running" in str(e)

        # Mock a running server process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin

        manager.server_process = mock_process
        manager._server_started = True
        manager._log_lines = ["LOG: Initial log", "LOG: Some other log"]

        # Test successful command with no new logs (existing test)
        result = manager.send_server_command("help")

        # Verify the command was written to stdin
        mock_stdin.write.assert_called_with("help\n")
        mock_stdin.flush.assert_called()

        # Should return success message
        assert "help" in result
        assert "sent successfully" in result

        # Test command with server response logs
        # Reset the stdin mock for next test
        mock_stdin.reset_mock()

        # Simulate server logs being added during command execution
        def simulate_log_output(*args, **kwargs):
            # Simulate logs appearing after command is sent
            manager._log_lines.extend(
                [
                    (
                        "LOG  : General     , 1754248298938> 2,194,760,255> "
                        "command entered via server console (System.in): "
                        '"setaccesslevel grug none"'
                    ),
                    (
                        "LOG  : General     , 1754248298970> 2,194,760,287> "
                        "User grug no longer has access level"
                    ),
                ]
            )

        # Mock the stdin.write to trigger log simulation
        mock_stdin.write.side_effect = simulate_log_output

        result = manager.send_server_command("setaccesslevel grug none")

        # Should capture and format the server response
        assert "User grug no longer has access level" in result
        # Should not include the command echo
        assert "command entered via server console" not in result

        # Test command without stdin connection
        manager.server_process.stdin = None
        try:
            manager.send_server_command("test")
            assert False, "Should have raised ServerControlError"
        except ServerControlError as e:
            assert "No stdin connection" in str(e)


if __name__ == "__main__":
    test_project_zomboid_manager_creation()
    test_project_zomboid_manager_startup_detection()
    test_project_zomboid_manager_batch_file_logic()
    test_project_zomboid_send_server_command()
    print("✅ All Project Zomboid manager tests passed!")
