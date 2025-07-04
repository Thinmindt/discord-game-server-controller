#!/usr/bin/env python3
"""
Command Line Interface for testing Discord bot commands locally.

This allows you to test all the bot functionality without needing to connect to Discord.
"""

import asyncio
import sys
from typing import List
from dataclasses import dataclass

from src.config import Config
from src.game_server_interface import GameServerAPI, GameServerConductor, ServerControlError
from src.server_factory import ServerFactory


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
        self.server_instances = {}
        print("🚀 Discord Bot CLI Testing Interface")
        print("Type 'help' for available commands or 'quit' to exit")
        print("-" * 50)

    def get_server_instance(self, game_type: str) -> tuple[GameServerAPI, GameServerConductor]:
        """Get or create server instances for the specified game type."""
        game_type = game_type.lower()

        if game_type not in self.server_instances:
            self.server_instances[game_type] = ServerFactory.create_server_instances(game_type)

        return self.server_instances[game_type]

    async def cmd_start(self, args: List[str]) -> None:
        """Start the game server."""
        game_type = args[0] if args else Config.DEFAULT_GAME
        ctx = MockContext()

        if not ServerFactory.is_supported_game(game_type):
            supported = ", ".join(ServerFactory.get_supported_games().keys())
            await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
            return

        try:
            api, server_conductor = self.get_server_instance(game_type)
            game_name = ServerFactory.get_supported_games()[game_type.lower()]
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        if not server_conductor.is_on:
            await ctx.send(f"Starting {game_name} server...")
            server_conductor.start_server()

            max_tries = 20
            tries = 0
            while tries < max_tries and not server_conductor.is_on:
                await asyncio.sleep(1)
                tries += 1

            if server_conductor.is_on:
                await ctx.send(f"{game_name} server started!")
            else:
                await ctx.send("Timeout occurred while starting up. Contact support.")
        else:
            await ctx.send(f"{game_name} server is already running.")

    async def cmd_stop(self, args: List[str]) -> None:
        """Stop the game server."""
        game_type = args[0] if args else Config.DEFAULT_GAME
        ctx = MockContext()

        if not ServerFactory.is_supported_game(game_type):
            supported = ", ".join(ServerFactory.get_supported_games().keys())
            await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
            return

        try:
            api, server_conductor = self.get_server_instance(game_type)
            game_name = ServerFactory.get_supported_games()[game_type.lower()]
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        wait_time = 10  # seconds
        extra_wait_allowance = 10  # give it an extra 10 seconds.
        if server_conductor.is_on:
            try:
                api.shutdown_server(wait_time=wait_time)
                await ctx.send(f"{game_name} server will shut down in {wait_time} seconds.")

                await asyncio.sleep(10)

                while server_conductor.is_on and extra_wait_allowance > 0:
                    wait_interval = 2
                    await asyncio.sleep(wait_interval)
                    extra_wait_allowance -= wait_interval

                await ctx.send(f"The {game_name} server is now off.")
            except Exception as error:
                await ctx.send(f"Error during shutdown: {error}")
        else:
            await ctx.send(f"{game_name} server is not running.")

    async def cmd_restart(self, args: List[str]) -> None:
        """Restart the game server."""
        game_type = args[0] if args else Config.DEFAULT_GAME
        ctx = MockContext()

        if not ServerFactory.is_supported_game(game_type):
            supported = ", ".join(ServerFactory.get_supported_games().keys())
            await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
            return

        try:
            api, server_conductor = self.get_server_instance(game_type)
            game_name = ServerFactory.get_supported_games()[game_type.lower()]
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        wait_time = 10  # seconds from shutdown command issued until the server stops.
        if server_conductor.is_on:
            try:
                api.shutdown_server(wait_time=10)
                await ctx.send(
                    f"{game_name} server shutting down in {wait_time} seconds "
                    f"to prepare for a reset. Log out now!"
                )
            except Exception as error:
                await ctx.send(f"Error during shutdown: {error}")
                return
            await asyncio.sleep(wait_time + 5)
            server_conductor.start_server()
            await ctx.send(f"{game_name} server restarted!")
        else:
            await ctx.send(f"{game_name} server is not running.")

    async def cmd_update(self, args: List[str]) -> None:
        """Update the server."""
        game_type = args[0] if args else Config.DEFAULT_GAME
        ctx = MockContext()

        if not ServerFactory.is_supported_game(game_type):
            supported = ", ".join(ServerFactory.get_supported_games().keys())
            await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
            return

        try:
            api, server_conductor = self.get_server_instance(game_type)
            game_name = ServerFactory.get_supported_games()[game_type.lower()]
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        if server_conductor.is_on:
            await ctx.send(f"The {game_name} server is running. Shut it down before updating.")
            return

        await ctx.send(f"Starting {game_name} server update. Please wait...")

        try:
            server_conductor.update_server()
            await ctx.send(f"{game_name} server update executed successfully.")
        except ServerControlError as error:
            await ctx.send(f"{game_name} server update failed: {error}")

    async def cmd_info(self, args: List[str]) -> None:
        """Display information about the running server."""
        game_type = args[0] if args else Config.DEFAULT_GAME
        ctx = MockContext()

        if not ServerFactory.is_supported_game(game_type):
            supported = ", ".join(ServerFactory.get_supported_games().keys())
            await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
            return

        try:
            api, server_conductor = self.get_server_instance(game_type)
            game_name = ServerFactory.get_supported_games()[game_type.lower()]
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        if server_conductor.is_on:
            info = api.get_server_info()

            server_info = [
                f"{game_name} Server Info:",
                f"Server Name: {info.server_name}",
                f"Version: {info.version}",
                f"Description: {info.description}",
            ]

            if info.max_players:
                server_info.append(f"Max Players: {info.max_players}")
            if info.current_players is not None:
                server_info.append(f"Current Players: {info.current_players}")
            if info.uptime:
                server_info.append(f"Uptime: {info.uptime}")

            # Add game-specific info
            if info.additional_info:
                for key, value in info.additional_info.items():
                    if key != "game_type":
                        server_info.append(f"{key.title()}: {value}")

            await ctx.send("\n".join(server_info))
        else:
            await ctx.send(f"The {game_name} server is off. We cannot retrieve information.")

    async def cmd_ip(self, args: List[str]) -> None:
        """Display the public IP address of the host."""
        game_type = args[0] if args else Config.DEFAULT_GAME
        ctx = MockContext()

        if not ServerFactory.is_supported_game(game_type):
            supported = ", ".join(ServerFactory.get_supported_games().keys())
            await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
            return

        try:
            api, server_conductor = self.get_server_instance(game_type)
            game_name = ServerFactory.get_supported_games()[game_type.lower()]
            port = server_conductor.get_default_port()
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        ip = Config.get_public_ip()
        await ctx.send(f"The {game_name} server host IP address is: {ip}:{port}")

    async def cmd_games(self, args: List[str]) -> None:
        """List all supported game types and their aliases."""
        ctx = MockContext()

        games = ServerFactory.get_supported_games()
        game_list = []

        # Group by full name to show aliases
        full_names = {}
        for alias, full_name in games.items():
            if full_name not in full_names:
                full_names[full_name] = []
            full_names[full_name].append(alias)

        for full_name, aliases in full_names.items():
            alias_str = ", ".join(f"`{alias}`" for alias in aliases)
            game_list.append(f"**{full_name}**: {alias_str}")

        await ctx.send(
            "Supported games:\n"
            + "\n".join(game_list)
            + f"\n\nDefault game: `{Config.DEFAULT_GAME}`"
        )

    def cmd_help(self, args: List[str]) -> None:
        """Show help information."""
        help_text = """
🤖 Discord Bot CLI Commands:

Game Server Commands:
  start [game_type]    - Start a game server (e.g., 'start pz', 'start palworld')
  stop [game_type]     - Stop a game server
  restart [game_type]  - Restart a game server
  update [game_type]   - Update a game server (must be stopped first)
  info [game_type]     - Get server information
  ip [game_type]       - Get server IP and port
  games               - List all supported games

CLI Commands:
  help                - Show this help message
  quit / exit         - Exit the CLI

Examples:
  start pz            - Start Project Zomboid server
  stop palworld       - Stop Palworld server
  info                - Get info for default game server
  games               - List all supported games

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
