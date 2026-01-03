"""
Unified command implementations for both Discord bot and CLI.

This module contains the actual command logic that can be shared between
the Discord bot (main.py) and CLI tester (cli_test.py).
"""

import asyncio
import queue
import threading
from typing import Protocol

from src.backup_manager import BackupResult, BackupUtility
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

    def __init__(self) -> None:
        self.server_managers: dict[str, GameServerManager] = {}

    def get_server_manager(self, game_type: str) -> GameServerManager:
        """Get or create server manager for the specified game type."""
        # First find the canonical game name for this game type
        canonical_name = self._find_supported_game(game_type)
        if not canonical_name:
            raise ValueError(f"Unsupported game type: {game_type}")

        # Use the canonical name as the key to ensure aliases share the same manager
        if canonical_name not in self.server_managers:
            manager = ServerFactory.create_server_manager(game_type)
            self.server_managers[canonical_name] = manager

        return self.server_managers[canonical_name]

    def _find_supported_game(self, game_type: str) -> str | None:
        """Find the game type in supported games, return the canonical name."""
        supported_games = ServerFactory.get_supported_games()
        game_type_lower = game_type.lower()

        for game_name, aliases in supported_games.items():
            if game_type_lower in aliases:
                return game_name
        return None

    def _get_all_supported_aliases(self) -> list[str]:
        """Get all supported game aliases as a flat list."""
        supported = []
        for game_name, aliases in ServerFactory.get_supported_games().items():
            supported.extend(aliases)
        return supported

    def _format_game_name(self, game_name: str) -> str:
        """Convert internal game name to display name."""
        return game_name.replace("_", " ").title()

    async def cmd_start(self, ctx: MessageContext, args: list[str]) -> None:
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
                await ctx.send(
                    "⏰ Timeout occurred while starting up. Contact support."
                )
        else:
            await ctx.send(f"✅ {display_name} server is already running.")

    async def cmd_stop(self, ctx: MessageContext, args: list[str]) -> None:
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

    async def cmd_restart(self, ctx: MessageContext, args: list[str]) -> None:
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
                    f"🔄 {display_name} server restarting. Players should log out now!"
                )

                # Stop the server
                manager.shutdown_server(wait_time=wait_time)
                await asyncio.sleep(2)  # Brief pause

                # Start the server
                manager.start_server()

                # Wait for startup
                max_tries = 5 * 60  # 5 minutes
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
            await ctx.send(
                f"⚠️ {display_name} server is not running. Use `start` instead."
            )

    async def cmd_update(self, ctx: MessageContext, args: list[str]) -> None:
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
                f"⚠️ The {display_name} server is running. Shut it down before updating."
            )
            return

        # Auto-backup before updating (if supported)
        try:
            await ctx.send("💾 Creating backup before update...")

            message_queue: queue.Queue[str | None] = queue.Queue()

            def progress_callback(message: str) -> None:
                message_queue.put(message)

            backup_result_holder: list[BackupResult | Exception] = []
            backup_complete = threading.Event()

            def run_backup() -> None:
                try:
                    result = manager.backup_server(progress_callback)
                    backup_result_holder.append(result)
                except Exception as e:
                    backup_result_holder.append(e)
                finally:
                    backup_complete.set()
                    message_queue.put(None)

            backup_thread = threading.Thread(target=run_backup)
            backup_thread.start()

            while not backup_complete.is_set() or not message_queue.empty():
                try:
                    message = message_queue.get(timeout=0.5)
                    if message is None:
                        break
                    await ctx.send(message)
                except queue.Empty:
                    await asyncio.sleep(0.1)

            backup_thread.join()

            if backup_result_holder and isinstance(backup_result_holder[0], Exception):
                error = backup_result_holder[0]
                if "No files found to backup" in str(error):
                    await ctx.send(
                        "⚠️ No existing save data to backup. Proceeding with update..."
                    )
                else:
                    await ctx.send(
                        f"⚠️ Backup failed: {error}. Proceeding with update anyway..."
                    )
            elif backup_result_holder and isinstance(
                backup_result_holder[0], BackupResult
            ):
                if backup_result_holder[0].success:
                    await ctx.send("✅ Backup completed!")

        except ServerControlError:
            # This game doesn't support backups, skip silently
            pass

        await ctx.send(f"⬇️ Starting {display_name} server update. Please wait...")

        try:
            manager.update_server()
            await ctx.send(f"✅ {display_name} server update executed successfully.")
        except ServerControlError as e:
            await ctx.send(f"❌ {display_name} server update failed: {e}")

    async def cmd_info(self, ctx: MessageContext, args: list[str]) -> None:
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
            await ctx.send(
                f"⚠️ The {display_name} server is off. We cannot retrieve information."
            )

    async def cmd_ip(self, ctx: MessageContext, args: list[str]) -> None:
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
        await ctx.send(
            f"🌐 The {display_name} server host IP address is: `{ip}:{port}`"
        )

    async def cmd_games(self, ctx: MessageContext, args: list[str]) -> None:
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

    async def cmd_cmd(self, ctx: MessageContext, args: list[str]) -> None:
        """Send an ad-hoc admin command to the running game server."""
        if len(args) < 2:
            await ctx.send(
                "❌ Usage: `cmd <game_type> <command> [args...]`\n"
                "Example: `cmd pz teleport player1 player2`\n"
                'Example: `cmd pz servermsg "Server maintenance in 5 minutes"`\n'
                "See https://pzwiki.net/wiki/Admin_commands for Project Zomboid commands."
            )
            return

        game_type = args[0]
        command_parts = args[1:]
        command = " ".join(command_parts)

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
            await ctx.send(
                f"⚠️ The {display_name} server is not running. Start it first."
            )
            return

        try:
            await ctx.send(f"📨 Sending command to {display_name} server: `{command}`")
            result = manager.send_server_command(command)

            # Limit response length to avoid Discord message limits
            if len(result) > 1500:
                result = result[:1500] + "... (output truncated)"

            await ctx.send(f"📥 Server response:\n```\n{result}\n```")

        except ServerControlError as e:
            await ctx.send(f"❌ Command failed: {e}")

    async def cmd_backup(self, ctx: MessageContext, args: list[str]) -> None:
        """Create a backup of the game server data."""
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

        await ctx.send(f"💾 Starting backup of {display_name} server...")

        try:
            # Use a thread-safe queue to communicate between backup thread and async loop
            message_queue: queue.Queue[str | None] = queue.Queue()
            result_holder: list[BackupResult | Exception] = []
            backup_complete = threading.Event()

            def progress_callback(message: str) -> None:
                """Called by backup_server to report progress."""
                message_queue.put(message)

            def run_backup() -> None:
                """Run backup in a separate thread."""
                try:
                    result = manager.backup_server(progress_callback)
                    result_holder.append(result)
                except Exception as e:
                    result_holder.append(e)
                finally:
                    backup_complete.set()
                    message_queue.put(None)  # Signal completion

            # Start backup in a separate thread
            backup_thread = threading.Thread(target=run_backup)
            backup_thread.start()

            # Process messages as they come in, with periodic "still working" messages
            last_message_time = asyncio.get_event_loop().time()
            still_working_interval = 10  # seconds

            while not backup_complete.is_set() or not message_queue.empty():
                try:
                    # Check for new messages with a short timeout
                    message = message_queue.get(timeout=0.5)
                    if message is None:
                        # Completion signal
                        break
                    await ctx.send(message)
                    last_message_time = asyncio.get_event_loop().time()
                except queue.Empty:
                    # No message available, check if we should send "still working"
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_message_time >= still_working_interval:
                        await ctx.send("⏳ Still working on backup...")
                        last_message_time = current_time
                    # Let other async tasks run
                    await asyncio.sleep(0.1)

            # Wait for backup thread to finish
            backup_thread.join()

            # Check result
            if not result_holder:
                raise ServerControlError("Backup failed unexpectedly")

            result_or_error = result_holder[0]
            if isinstance(result_or_error, Exception):
                raise ServerControlError(str(result_or_error))

            result: BackupResult = result_or_error

            if result.success:
                # Get recent backups for display using BackupUtility
                backup_dir = result.backup_path.parent if result.backup_path else None
                server_name = getattr(manager, "server_name", None)

                if backup_dir and server_name:
                    backup_utility = BackupUtility(backup_dir, server_name)
                    recent_backups = backup_utility.get_recent_backups(count=3)
                    if recent_backups:
                        backup_list = "\n".join(f"  • {ts}" for ts in recent_backups)
                        await ctx.send(
                            f"✅ {display_name} backup completed successfully!\n\n"
                            f"**Recent backups:**\n{backup_list}"
                        )
                    else:
                        await ctx.send(
                            f"✅ {display_name} backup completed successfully!"
                        )
                else:
                    await ctx.send(f"✅ {display_name} backup completed successfully!")
            else:
                await ctx.send(
                    f"⚠️ {display_name} backup completed with warnings: {result.message}"
                )

        except ServerControlError as e:
            await ctx.send(f"❌ Backup failed: {e}")

    async def cmd_version(self, ctx: MessageContext, args: list[str]) -> None:
        """Display the current server version/branch."""
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

        # Check if this game supports version detection
        try:
            version_info = manager.get_version()
        except ServerControlError:
            await ctx.send(f"⚠️ {display_name} does not support version detection.")
            return

        branch_display = version_info.get(
            "branch_display", version_info.get("branch", "Unknown")
        )
        server_name = version_info.get("server_name", "Unknown")

        status = "🟢 Running" if manager.is_on() else "🔴 Stopped"

        await ctx.send(
            f"📦 **{display_name} Version Info**\n"
            f"Version: {branch_display}\n"
            f"Server Name: `{server_name}`\n"
            f"Status: {status}"
        )

    async def cmd_setversion(self, ctx: MessageContext, args: list[str]) -> None:
        """Switch the server to a different version/branch."""
        if len(args) < 2:
            await ctx.send(
                "❌ Usage: `setversion <game_type> <version>`\n"
                "Examples:\n"
                "  `setversion pz stable` - Switch to Build 41 (stable)\n"
                "  `setversion pz beta` - Switch to Build 42 (beta)\n"
                "  `setversion pz b41` - Switch to Build 41\n"
                "  `setversion pz b42` - Switch to Build 42"
            )
            return

        game_type = args[0]
        target_branch = args[1]

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

        # Check if server is running
        if manager.is_on():
            await ctx.send(
                f"⚠️ The {display_name} server is running. "
                "Please stop it first with `stop` before switching versions."
            )
            return

        # Check if this game supports version switching
        try:
            # First, create a backup before switching
            await ctx.send("💾 Creating backup before version switch...")

            # Use the backup method with progress callback
            message_queue: queue.Queue[str | None] = queue.Queue()

            def progress_callback(message: str) -> None:
                message_queue.put(message)

            # Run backup in thread
            backup_result_holder: list[BackupResult | Exception] = []
            backup_complete = threading.Event()

            def run_backup() -> None:
                try:
                    result = manager.backup_server(progress_callback)
                    backup_result_holder.append(result)
                except Exception as e:
                    backup_result_holder.append(e)
                finally:
                    backup_complete.set()
                    message_queue.put(None)

            backup_thread = threading.Thread(target=run_backup)
            backup_thread.start()

            # Process backup messages
            while not backup_complete.is_set() or not message_queue.empty():
                try:
                    message = message_queue.get(timeout=0.5)
                    if message is None:
                        break
                    await ctx.send(message)
                except queue.Empty:
                    await asyncio.sleep(0.1)

            backup_thread.join()

            if backup_result_holder and isinstance(backup_result_holder[0], Exception):
                # Backup failed, but we might continue if there's nothing to back up
                error = backup_result_holder[0]
                if "No files found to backup" in str(error):
                    await ctx.send(
                        "⚠️ No existing save data found for current version. "
                        "Proceeding with version switch..."
                    )
                else:
                    await ctx.send(f"❌ Backup failed: {error}")
                    return
            elif backup_result_holder and isinstance(
                backup_result_holder[0], BackupResult
            ):
                backup_result = backup_result_holder[0]
                if backup_result.success:
                    await ctx.send("✅ Backup completed successfully!")

            # Now switch versions
            await ctx.send(
                f"🔄 Switching {display_name} to version `{target_branch}`..."
            )
            await ctx.send("⏳ Running SteamCMD update. This may take a few minutes...")

            result = manager.set_version(target_branch)
            await ctx.send(result)

        except ServerControlError as e:
            await ctx.send(f"❌ Version switch failed: {e}")

    async def cmd_available_versions(
        self, ctx: MessageContext, args: list[str]
    ) -> None:
        """Display the available versions/branches for a game server."""
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

        # Check if this game supports version listing
        try:
            versions = manager.get_available_versions()
        except ServerControlError:
            await ctx.send(f"⚠️ {display_name} does not support version selection.")
            return

        version_lines = []
        for v in versions:
            selected_marker = " ✅ (current)" if v.get("selected") else ""
            version_lines.append(
                f"• **{v['name']}**{selected_marker}\n  {v['description']}"
            )

        await ctx.send(
            f"📋 **Available {display_name} Versions**\n\n"
            + "\n".join(version_lines)
            + "\n\nUse `setversion <game> <version>` to switch."
        )


# Global instance that can be shared
game_commands = GameServerCommands()
