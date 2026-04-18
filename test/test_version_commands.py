"""Tests for version-related Discord command handlers."""

import asyncio
import pathlib
from unittest.mock import MagicMock, patch

from src.backup_manager import BackupResult
from src.game_commands import GameServerCommands
from src.game_server_interface import ServerControlError


class MockMessageContext:
    """Mock message context for testing."""

    def __init__(self):
        self.messages = []

    async def send(self, message: str) -> None:
        """Store sent messages for testing."""
        self.messages.append(message)


class TestCmdVersion:
    """Tests for the !version command handler."""

    def test_version_unsupported_game(self):
        """Test version command with unsupported game type."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        asyncio.run(commands.cmd_version(ctx, ["unsupported_game"]))

        assert len(ctx.messages) == 1
        assert "Unsupported game type" in ctx.messages[0]

    def test_version_game_without_version_support(self):
        """Test version command with a game that doesn't support versions."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.get_version.side_effect = ServerControlError("Not supported")
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_version(ctx, ["pz"]))

            assert len(ctx.messages) == 1
            assert "does not support version detection" in ctx.messages[0]

    def test_version_shows_current_version(self):
        """Test version command shows correct version info."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.get_version.return_value = {
                "branch": "stable",
                "branch_display": "Build 41 (Stable)",
                "server_name": "testserver",
            }
            mock_manager.is_on.return_value = False
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_version(ctx, ["pz"]))

            assert len(ctx.messages) == 1
            assert "Build 41" in ctx.messages[0]
            assert "testserver" in ctx.messages[0]
            assert "Stopped" in ctx.messages[0]

    def test_version_shows_running_status(self):
        """Test version command shows running status correctly."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.get_version.return_value = {
                "branch": "beta",
                "branch_display": "Build 42 (Beta)",
                "server_name": "testserver_b42",
            }
            mock_manager.is_on.return_value = True
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_version(ctx, ["pz"]))

            assert len(ctx.messages) == 1
            assert "Running" in ctx.messages[0]


class TestCmdSetVersion:
    """Tests for the !setversion command handler."""

    def test_setversion_missing_args(self):
        """Test setversion command with missing arguments."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        asyncio.run(commands.cmd_setversion(ctx, []))

        assert len(ctx.messages) == 1
        assert "Usage:" in ctx.messages[0]

    def test_setversion_missing_version_arg(self):
        """Test setversion command with only game type."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        asyncio.run(commands.cmd_setversion(ctx, ["pz"]))

        assert len(ctx.messages) == 1
        assert "Usage:" in ctx.messages[0]

    def test_setversion_unsupported_game(self):
        """Test setversion command with unsupported game type."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        asyncio.run(commands.cmd_setversion(ctx, ["unsupported_game", "beta"]))

        assert len(ctx.messages) == 1
        assert "Unsupported game type" in ctx.messages[0]

    def test_setversion_server_running(self):
        """Test setversion command when server is running."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.is_on.return_value = True
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_setversion(ctx, ["pz", "beta"]))

            assert len(ctx.messages) == 1
            assert "running" in ctx.messages[0].lower()
            assert "stop" in ctx.messages[0].lower()

    def test_setversion_successful_switch(self):
        """Test successful version switch."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.is_on.return_value = False
            # Simulate no files to backup - message must contain "No files found to backup"
            mock_manager.backup_server.side_effect = ServerControlError(
                "No files found to backup for server"
            )
            mock_manager.set_version.return_value = "Successfully switched to Build 42 (Beta)!"
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_setversion(ctx, ["pz", "beta"]))

            # Should have backup message, proceeding message, switching message, and result
            assert any("backup" in m.lower() for m in ctx.messages)
            assert any("switched" in m.lower() or "Build 42" in m for m in ctx.messages)

    def test_setversion_with_successful_backup(self):
        """Test version switch with successful backup."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.is_on.return_value = False
            mock_manager.backup_server.return_value = BackupResult(
                success=True,
                backup_path=pathlib.Path("/backups/test"),
                message="Backup complete",
                files_backed_up=["file1", "file2"],
            )
            mock_manager.set_version.return_value = "Successfully switched!"
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_setversion(ctx, ["pz", "beta"]))

            # Should have backup success message
            assert any("backup" in m.lower() and "completed" in m.lower() for m in ctx.messages)


class TestCmdAvailableVersions:
    """Tests for the !available_versions command handler."""

    def test_available_versions_unsupported_game(self):
        """Test available_versions command with unsupported game type."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        asyncio.run(commands.cmd_available_versions(ctx, ["unsupported_game"]))

        assert len(ctx.messages) == 1
        assert "Unsupported game type" in ctx.messages[0]

    def test_available_versions_game_without_support(self):
        """Test available_versions with game that doesn't support versions."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.get_available_versions.side_effect = ServerControlError("Not supported")
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_available_versions(ctx, ["pz"]))

            assert len(ctx.messages) == 1
            assert "does not support version selection" in ctx.messages[0]

    def test_available_versions_shows_versions(self):
        """Test available_versions shows all versions."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.get_available_versions.return_value = [
                {
                    "id": "stable",
                    "name": "Build 41 (Stable)",
                    "description": "Current stable release",
                    "selected": True,
                },
                {
                    "id": "beta",
                    "name": "Build 42 (Beta)",
                    "description": "Unstable beta branch",
                    "selected": False,
                },
            ]
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_available_versions(ctx, ["pz"]))

            assert len(ctx.messages) == 1
            assert "Build 41" in ctx.messages[0]
            assert "Build 42" in ctx.messages[0]
            assert "current" in ctx.messages[0].lower()  # Should indicate current selection

    def test_available_versions_shows_setversion_hint(self):
        """Test available_versions shows how to switch."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.get_available_versions.return_value = [
                {
                    "id": "stable",
                    "name": "Stable",
                    "description": "Stable",
                    "selected": True,
                },
            ]
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_available_versions(ctx, ["pz"]))

            assert len(ctx.messages) == 1
            assert "setversion" in ctx.messages[0].lower()


class TestCmdUpdateWithBackup:
    """Tests for the !update command auto-backup behavior."""

    def test_update_creates_backup_before_updating(self):
        """Test that update creates a backup before running SteamCMD."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.is_on.return_value = False
            mock_manager.backup_server.return_value = BackupResult(
                success=True,
                backup_path=pathlib.Path("/backups/test"),
                message="Backup complete",
                files_backed_up=["file1"],
            )
            mock_manager.update_server.return_value = None
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_update(ctx, ["pz"]))

            # Backup should be called before update
            mock_manager.backup_server.assert_called_once()
            mock_manager.update_server.assert_called_once()

            # Should have backup messages
            assert any("backup" in m.lower() for m in ctx.messages)

    def test_update_continues_if_backup_fails(self):
        """Test that update continues even if backup fails."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.is_on.return_value = False
            mock_manager.backup_server.side_effect = Exception("Backup failed")
            mock_manager.update_server.return_value = None
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_update(ctx, ["pz"]))

            # Update should still be called
            mock_manager.update_server.assert_called_once()

            # Should have warning about backup failure
            assert any("backup" in m.lower() and "failed" in m.lower() for m in ctx.messages)

    def test_update_skips_backup_for_unsupported_games(self):
        """Test that update skips backup gracefully for games without backup support."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.is_on.return_value = False
            mock_manager.backup_server.side_effect = ServerControlError(
                "This game server does not support backups"
            )
            mock_manager.update_server.return_value = None
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_update(ctx, ["pz"]))

            # Update should still be called
            mock_manager.update_server.assert_called_once()

    def test_update_server_running_blocked(self):
        """Test that update is blocked when server is running."""
        commands = GameServerCommands()
        ctx = MockMessageContext()

        with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
            mock_manager = MagicMock()
            mock_manager.is_on.return_value = True
            mock_factory.return_value = mock_manager

            asyncio.run(commands.cmd_update(ctx, ["pz"]))

            # Should not call backup or update
            mock_manager.backup_server.assert_not_called()
            mock_manager.update_server.assert_not_called()

            # Should warn user
            assert len(ctx.messages) == 1
            assert "running" in ctx.messages[0].lower()
