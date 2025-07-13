"""
Unified command implementations for both Discord bot and CLI.

This module contains the actual command logic that can be shared between
the Discord bot (main.py) and CLI tester (cli_test.py).
"""

import asyncio
from typing import List, Optional, Protocol, Dict, cast

from src.config import Config
from src.game_server_interface import GameServerManager, ServerControlError
from src.server_factory import ServerFactory


class MessageContext(Protocol):
    """Protocol for message context that works with both Discord and CLI."""

    async def send(self, message: str) -> None:
        """Send a message to the user."""
        ...


class GameServerCommands:
    """Unified command implementations for game server management."""

    def __init__(self):
        self.server_managers: Dict[str, GameServerManager] = {}

    def get_server_manager(self, game_type: str) -> GameServerManager:
        """Get or create server manager for the specified game type."""
        game_type = game_type.lower()

        if game_type not in self.server_managers:
            manager = cast(GameServerManager, ServerFactory.create_server_manager(game_type))
            self.server_managers[game_type] = manager

        return self.server_managers[game_type]

    def _find_supported_game(self, game_type: str) -> Optional[str]:
        """Find the game type in supported games, return the canonical name."""
        supported_games = ServerFactory.get_supported_games()
        game_type_lower = game_type.lower()

        for game_name, aliases in supported_games.items():
            if game_type_lower in aliases:
                return cast(str, game_name)
        return None
        return None

    def _get_all_supported_aliases(self) -> List[str]:
        """Get all supported game aliases as a flat list."""
        supported = []
        for game_name, aliases in ServerFactory.get_supported_games().items():
            supported.extend(aliases)
        return supported

    def _format_game_name(self, game_name: str) -> str:
        """Convert internal game name to display name."""
        return game_name.replace("_", " ").title()

    async def cmd_start(self, ctx: MessageContext, args: List[str]) -> None:
        """Start the game server."""
        game_type = args[0] if args else Config.DEFAULT_GAME

        # Check if the game type is supported
        found_game = self._find_supported_game(game_type)

        if not found_game:
            supported = self._get_all_supported_aliases()
            await ctx.send(
                f"Unsupported game type '{game_type}'. Supported games: {', '.join(supported)}"
            )
            return

        try:
            manager = self.get_server_manager(game_type)
            display_name = self._format_game_name(found_game)
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        if not manager.is_on():
            await ctx.send(f"Starting {display_name} server...")
            try:
                manager.start_server()
            except ServerControlError as e:
                await ctx.send(f"Failed to start server: {e}")
                return

            # Wait for server to start up
            max_tries = 5 * 60  # 5 minutes
            tries = 0
            while tries < max_tries and not manager.is_on():
                await asyncio.sleep(1)
                tries += 1

            if manager.is_on():
                await ctx.send(f"🎉 {display_name} server started!")
            else:
                await ctx.send("⏰ Timeout occurred while starting up. Contact support.")
        else:
            await ctx.send(f"✅ {display_name} server is already running.")

    async def cmd_stop(self, ctx: MessageContext, args: List[str]) -> None:
        """Stop the game server."""
        game_type = args[0] if args else Config.DEFAULT_GAME

        found_game = self._find_supported_game(game_type)

        if not found_game:
            supported = self._get_all_supported_aliases()
            await ctx.send(
                f"Unsupported game type '{game_type}'. Supported games: {', '.join(supported)}"
            )
            return

        try:
            manager = self.get_server_manager(game_type)
            display_name = self._format_game_name(found_game)
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        wait_time = 30  # seconds
        if manager.is_on():
            try:
                await ctx.send(f"🛑 Shutting down {display_name} server...")
                manager.shutdown_server(wait_time=wait_time)
                await ctx.send(f"✅ {display_name} server has been shut down.")
            except ServerControlError as e:
                await ctx.send(f"❌ Error during shutdown: {e}")
        else:
            await ctx.send(f"⚠️ {display_name} server is not running.")

    async def cmd_restart(self, ctx: MessageContext, args: List[str]) -> None:
        """Restart the game server."""
        game_type = args[0] if args else Config.DEFAULT_GAME

        found_game = self._find_supported_game(game_type)

        if not found_game:
            supported = self._get_all_supported_aliases()
            await ctx.send(
                f"Unsupported game type '{game_type}'. Supported games: {', '.join(supported)}"
            )
            return

        try:
            manager = self.get_server_manager(game_type)
            display_name = self._format_game_name(found_game)
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        if manager.is_on():
            wait_time = 30
            try:
                await ctx.send(
                    f"🔄 {display_name} server restarting. " f"Players should log out now!"
                )

                # Stop the server
                manager.shutdown_server(wait_time=wait_time)
                await asyncio.sleep(2)  # Brief pause

                # Start the server
                manager.start_server()

                # Wait for startup
                max_tries = 20
                tries = 0
                while tries < max_tries and not manager.is_on():
                    await asyncio.sleep(1)
                    tries += 1

                if manager.is_on():
                    await ctx.send(f"✅ {display_name} server restarted successfully!")
                else:
                    await ctx.send("⚠️ Server restart may have failed. Check manually.")

            except ServerControlError as e:
                await ctx.send(f"❌ Error during restart: {e}")
        else:
            await ctx.send(f"⚠️ {display_name} server is not running. Use `start` instead.")

    async def cmd_update(self, ctx: MessageContext, args: List[str]) -> None:
        """Update the server."""
        game_type = args[0] if args else Config.DEFAULT_GAME

        found_game = self._find_supported_game(game_type)

        if not found_game:
            supported = self._get_all_supported_aliases()
            await ctx.send(
                f"Unsupported game type '{game_type}'. Supported games: {', '.join(supported)}"
            )
            return

        try:
            manager = self.get_server_manager(game_type)
            display_name = self._format_game_name(found_game)
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        if manager.is_on():
            await ctx.send(
                f"⚠️ The {display_name} server is running. " f"Shut it down before updating."
            )
            return

        await ctx.send(f"⬇️ Starting {display_name} server update. Please wait...")

        try:
            manager.update_server()
            await ctx.send(f"✅ {display_name} server update executed successfully.")
        except ServerControlError as e:
            await ctx.send(f"❌ {display_name} server update failed: {e}")

    async def cmd_info(self, ctx: MessageContext, args: List[str]) -> None:
        """Display information about the running server."""
        game_type = args[0] if args else Config.DEFAULT_GAME

        found_game = self._find_supported_game(game_type)

        if not found_game:
            supported = self._get_all_supported_aliases()
            await ctx.send(
                f"Unsupported game type '{game_type}'. Supported games: {', '.join(supported)}"
            )
            return

        try:
            manager = self.get_server_manager(game_type)
            display_name = self._format_game_name(found_game)
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        if manager.is_on():
            try:
                info = manager.get_server_info()

                server_info = [
                    f"📊 {display_name} Server Info:",
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
                            formatted_key = key.replace("_", " ").title()
                            server_info.append(f"{formatted_key}: {value}")

                await ctx.send("\n".join(server_info))
            except ServerControlError as e:
                await ctx.send(f"❌ Could not retrieve server info: {e}")
        else:
            await ctx.send(f"⚠️ The {display_name} server is off. We cannot retrieve information.")

    async def cmd_ip(self, ctx: MessageContext, args: List[str]) -> None:
        """Display the public IP address of the host."""
        game_type = args[0] if args else Config.DEFAULT_GAME

        found_game = self._find_supported_game(game_type)

        if not found_game:
            supported = self._get_all_supported_aliases()
            await ctx.send(
                f"Unsupported game type '{game_type}'. Supported games: {', '.join(supported)}"
            )
            return

        try:
            manager = self.get_server_manager(game_type)
            display_name = self._format_game_name(found_game)
            port = manager.get_default_port()
        except ValueError as e:
            await ctx.send(f"Error: {str(e)}")
            return

        ip = Config.get_public_ip()
        await ctx.send(f"🌐 The {display_name} server host IP address is: `{ip}:{port}`")

    async def cmd_games(self, ctx: MessageContext, args: List[str]) -> None:
        """List all supported game types and their aliases."""
        games = ServerFactory.get_supported_games()
        game_list = []

        # The format is {game_name: [aliases]}
        for full_name, aliases in games.items():
            # Convert to human-readable format
            display_name = self._format_game_name(full_name)
            alias_str = ", ".join(f"`{alias}`" for alias in aliases)
            game_list.append(f"**{display_name}**: {alias_str}")

        await ctx.send(
            "🎮 Supported games:\n"
            + "\n".join(game_list)
            + f"\n\nDefault game: `{Config.DEFAULT_GAME}`"
        )


# Global instance that can be shared
game_commands = GameServerCommands()
