"""Test the new cmd functionality for sending ad-hoc commands to game servers."""

from unittest.mock import MagicMock, patch

from src.game_commands import GameServerCommands
from src.game_server_interface import ServerControlError


class MockMessageContext:
    """Mock message context for testing."""

    def __init__(self):
        self.messages = []

    async def send(self, message: str) -> None:
        """Store sent messages for testing."""
        self.messages.append(message)


def test_cmd_command_usage_validation():
    """Test that cmd command validates usage properly."""
    commands = GameServerCommands()
    ctx = MockMessageContext()

    # Test missing arguments
    import asyncio

    asyncio.run(commands.cmd_cmd(ctx, []))

    assert len(ctx.messages) == 1
    assert "Usage:" in ctx.messages[0]
    assert "cmd <game_type> <command>" in ctx.messages[0]

    # Test insufficient arguments (only game type)
    ctx.messages.clear()
    asyncio.run(commands.cmd_cmd(ctx, ["pz"]))

    assert len(ctx.messages) == 1
    assert "Usage:" in ctx.messages[0]


def test_cmd_command_unsupported_game():
    """Test cmd command with unsupported game type."""
    commands = GameServerCommands()
    ctx = MockMessageContext()

    import asyncio

    asyncio.run(commands.cmd_cmd(ctx, ["unsupported_game", "help"]))

    assert len(ctx.messages) == 1
    assert "Unsupported game type" in ctx.messages[0]


def test_cmd_command_server_not_running():
    """Test cmd command when server is not running."""
    commands = GameServerCommands()
    ctx = MockMessageContext()

    # Mock the server manager to return False for is_on()
    with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
        mock_manager = MagicMock()
        mock_manager.is_on.return_value = False
        mock_factory.return_value = mock_manager

        import asyncio

        asyncio.run(commands.cmd_cmd(ctx, ["pz", "help"]))

        assert len(ctx.messages) == 1
        assert "server is not running" in ctx.messages[0]


def test_cmd_command_successful_execution():
    """Test successful cmd command execution."""
    commands = GameServerCommands()
    ctx = MockMessageContext()

    # Mock the server manager
    with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
        mock_manager = MagicMock()
        mock_manager.is_on.return_value = True
        mock_manager.send_server_command.return_value = "Command executed successfully"
        mock_factory.return_value = mock_manager

        import asyncio

        asyncio.run(commands.cmd_cmd(ctx, ["pz", "teleport", "player1", "player2"]))

        # Should have sent command and received response
        assert len(ctx.messages) == 2
        assert "Sending command" in ctx.messages[0]
        assert "teleport player1 player2" in ctx.messages[0]
        assert "Server response:" in ctx.messages[1]
        assert "Command executed successfully" in ctx.messages[1]

        # Verify the manager was called with the right command
        mock_manager.send_server_command.assert_called_with("teleport player1 player2")


def test_cmd_command_server_error():
    """Test cmd command when server returns an error."""
    commands = GameServerCommands()
    ctx = MockMessageContext()

    # Mock the server manager to raise an error
    with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
        mock_manager = MagicMock()
        mock_manager.is_on.return_value = True
        mock_manager.send_server_command.side_effect = ServerControlError("Command failed")
        mock_factory.return_value = mock_manager

        import asyncio

        asyncio.run(commands.cmd_cmd(ctx, ["pz", "invalid_command"]))

        # Should have attempted to send command and received error
        assert len(ctx.messages) == 2
        assert "Sending command" in ctx.messages[0]
        assert "Command failed:" in ctx.messages[1]
        assert "Command failed" in ctx.messages[1]


def test_cmd_command_long_output_truncation():
    """Test that long server output is truncated appropriately."""
    commands = GameServerCommands()
    ctx = MockMessageContext()

    # Mock the server manager with very long response
    long_response = "A" * 2000  # Longer than 1500 character limit
    with patch("src.server_factory.ServerFactory.create_server_manager") as mock_factory:
        mock_manager = MagicMock()
        mock_manager.is_on.return_value = True
        mock_manager.send_server_command.return_value = long_response
        mock_factory.return_value = mock_manager

        import asyncio

        asyncio.run(commands.cmd_cmd(ctx, ["pz", "help"]))

        # Should have truncated the response
        assert len(ctx.messages) == 2
        assert "Sending command" in ctx.messages[0]
        assert "output truncated" in ctx.messages[1]
        # The actual response should be shorter
        response_content = ctx.messages[1]
        assert len(response_content) < 2000


if __name__ == "__main__":
    test_cmd_command_usage_validation()
    test_cmd_command_unsupported_game()
    test_cmd_command_server_not_running()
    test_cmd_command_successful_execution()
    test_cmd_command_server_error()
    test_cmd_command_long_output_truncation()
    print("✅ All cmd functionality tests passed!")
