#!/usr/bin/env python3
"""
Command Line Interface for testing Discord bot commands locally.

This allows you to test all the bot functionality without needing to connect to Discord.
"""

import asyncio
import sys
from typing import List
from dataclasses import dataclass

from src.config import Config  # noqa: F401 - used in docstring
from src.game_commands import game_commands


@dataclass
class MockContext:
    """Mock Discord context for CLI testing."""

    def __init__(self):
        self.messages: List[str] = []

    async def send(self, message: str) -> None:
        """Mock the Discord ctx.send() method."""
        print(f"🤖 Bot: {message}")
        self.messages.append(message)


class DiscordBotCLI:
    """Command line interface for testing Discord bot commands."""

    def __init__(self):
        print("🚀 Discord Bot CLI Testing Interface")
        print("Type 'help' for available commands or 'quit' to exit")
        print("-" * 50)

    async def cmd_start(self, args: List[str]) -> None:
        """Start the game server."""
        ctx = MockContext()
        await game_commands.cmd_start(ctx, args)

    async def cmd_stop(self, args: List[str]) -> None:
        """Stop the game server."""
        ctx = MockContext()
        await game_commands.cmd_stop(ctx, args)

    async def cmd_restart(self, args: List[str]) -> None:
        """Restart the game server."""
        ctx = MockContext()
        await game_commands.cmd_restart(ctx, args)

    async def cmd_update(self, args: List[str]) -> None:
        """Update the server."""
        ctx = MockContext()
        await game_commands.cmd_update(ctx, args)

    async def cmd_info(self, args: List[str]) -> None:
        """Display information about the running server."""
        ctx = MockContext()
        await game_commands.cmd_info(ctx, args)

    async def cmd_ip(self, args: List[str]) -> None:
        """Display the public IP address of the host."""
        ctx = MockContext()
        await game_commands.cmd_ip(ctx, args)

    async def cmd_games(self, args: List[str]) -> None:
        """List all supported game types and their aliases."""
        ctx = MockContext()
        await game_commands.cmd_games(ctx, args)

    async def cmd_cmd(self, args: List[str]) -> None:
        """Send an ad-hoc admin command to the running game server."""
        ctx = MockContext()
        await game_commands.cmd_cmd(ctx, args)

    def cmd_help(self, args: List[str]) -> None:
        """Show help information."""
        help_text = """
🤖 Discord Bot CLI Commands:

Game Server Commands:
  start [game_type]         - Start a game server (e.g., 'start pz', 'start palworld')
  stop [game_type]          - Stop a game server
  restart [game_type]       - Restart a game server
  update [game_type]        - Update a game server (must be stopped first)
  info [game_type]          - Get server information
  ip [game_type]            - Get server IP and port
  cmd <game_type> <command> - Send admin command to running server
  games                     - List all supported games

CLI Commands:
  help                      - Show this help message
  quit / exit               - Exit the CLI

Examples:
  start pz                     - Start Project Zomboid server
  stop palworld                - Stop Palworld server
  info                         - Get info for default game server
  cmd pz teleport player1 player2  - Teleport player1 to player2 in Project Zomboid
  cmd pz servermsg "Hello all"      - Broadcast message in Project Zomboid
  games                        - List all supported games

Note: If no game_type is specified, the default game will be used.
Default game: {Config.DEFAULT_GAME}
        """
        print(help_text)

    async def run(self) -> None:
        """Main CLI loop."""
        while True:
            try:
                user_input = input("\n💬 You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["quit", "exit"]:
                    print("👋 Goodbye!")
                    break

                # Parse command and arguments
                parts = user_input.split()
                command = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []

                # Handle commands
                if command == "help":
                    self.cmd_help(args)
                elif command == "start":
                    await self.cmd_start(args)
                elif command == "stop":
                    await self.cmd_stop(args)
                elif command == "restart":
                    await self.cmd_restart(args)
                elif command == "update":
                    await self.cmd_update(args)
                elif command == "info":
                    await self.cmd_info(args)
                elif command == "ip":
                    await self.cmd_ip(args)
                elif command == "games":
                    await self.cmd_games(args)
                elif command == "cmd":
                    await self.cmd_cmd(args)
                else:
                    print(f"❌ Unknown command: {command}")
                    print("Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")


def main():
    """Main entry point for the CLI."""
    try:
        cli = DiscordBotCLI()
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
