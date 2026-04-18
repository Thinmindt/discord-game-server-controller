from typing import Any

import discord
from discord.ext import commands

from src.config import Config
from src.game_commands import game_commands

COMMAND_PREFIX = "!"


class DiscordContext:
    """Adapter to make Discord context compatible with MessageContext protocol."""

    def __init__(self, ctx: commands.Context[Any]) -> None:
        self.ctx = ctx

    async def send(self, message: str) -> None:
        """Send a message to Discord."""
        await self.ctx.send(message)


# These interact with Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)


@bot.command(name="start")
async def start_server(ctx: commands.Context[Any], game_type: str | None = None) -> None:
    """Start the game server.

    Usage: !start [game_type]
    Examples: !start pz, !start palworld, !start
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_start(discord_ctx, args)


@bot.command(name="restart")
async def restart_server(ctx: commands.Context[Any], game_type: str | None = None) -> None:
    """Restart the game server.

    Usage: !restart [game_type]
    Examples: !restart pz, !restart palworld, !restart
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_restart(discord_ctx, args)


@bot.command(name="stop")
async def stop_server(ctx: commands.Context[Any], game_type: str | None = None) -> None:
    """Stop and close the game server.

    Usage: !stop [game_type]
    Examples: !stop pz, !stop palworld, !stop
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_stop(discord_ctx, args)


@bot.command(name="update")
async def update_server(ctx: commands.Context[Any], game_type: str | None = None) -> None:
    """Update the server. You must stop the server before updating.

    Usage: !update [game_type]
    Examples: !update pz, !update palworld, !update
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_update(discord_ctx, args)


@bot.command(name="info")
async def get_info(ctx: commands.Context[Any], game_type: str | None = None) -> None:
    """Display information about the running server.

    Usage: !info [game_type]
    Examples: !info pz, !info palworld, !info
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_info(discord_ctx, args)


@bot.command(name="ip")
async def get_ip(ctx: commands.Context[Any], game_type: str | None = None) -> None:
    """Display the public IP address of the host.

    Usage: !ip [game_type]
    Examples: !ip pz, !ip palworld, !ip
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_ip(discord_ctx, args)


@bot.command(name="games")
async def list_games(ctx: commands.Context[Any]) -> None:
    """List all supported game types and their aliases."""
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_games(discord_ctx, [])


@bot.command(name="cmd")
async def send_server_command(ctx: commands.Context[Any], *args: str) -> None:
    """Send an ad-hoc admin command to the running game server.

    Usage: !cmd <game_type> <command> [args...]
    Examples:
      !cmd pz teleport player1 player2
      !cmd pz servermsg "Server maintenance in 5 minutes"
      !cmd pz additem "player1" "Base.Axe" 5

    See https://pzwiki.net/wiki/Admin_commands for Project Zomboid commands.
    """
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_cmd(discord_ctx, list(args))


@bot.command(name="backup")
async def backup_server(ctx: commands.Context[Any], game_type: str | None = None) -> None:
    """Create a backup of the game server data.

    Usage: !backup [game_type]
    Examples: !backup pz, !backup, !backup project_zomboid

    The server must be stopped before creating a backup.
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_backup(discord_ctx, args)


@bot.command(name="version")
async def get_version(ctx: commands.Context[Any], game_type: str | None = None) -> None:
    """Display the current server version/branch.

    Usage: !version [game_type]
    Examples: !version pz, !version

    Shows the current version (stable/beta) and server name.
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_version(discord_ctx, args)


@bot.command(name="setversion")
async def set_version(
    ctx: commands.Context[Any], game_type: str | None = None, version: str | None = None
) -> None:
    """Switch the server to a different version/branch.

    Usage: !setversion <game_type> <version>
    Examples:
      !setversion pz stable - Switch to Build 41 (stable)
      !setversion pz beta - Switch to Build 42 (beta)
      !setversion pz b41 - Switch to Build 41
      !setversion pz b42 - Switch to Build 42

    The server must be stopped before switching versions.
    A backup will be created automatically before switching.
    """
    args = []
    if game_type:
        args.append(game_type)
    if version:
        args.append(version)
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_setversion(discord_ctx, args)


@bot.command(name="available_versions")
async def available_versions(ctx: commands.Context[Any], game_type: str | None = None) -> None:
    """Display the available versions/branches for a game server.

    Usage: !available_versions [game_type]
    Examples: !available_versions pz, !available_versions

    Shows all supported versions and indicates which is currently selected.
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_available_versions(discord_ctx, args)


@bot.command(name="configdiff")
async def configdiff(ctx: commands.Context[Any], game_type: str | None = None) -> None:
    """Compare configuration files between server versions.

    Usage: !configdiff [game_type]
    Examples: !configdiff pz, !configdiff

    Compares important settings between stable (B41) and beta (B42) configs,
    highlighting differences like AdminPassword, ports, and server settings.
    Useful when switching versions to ensure settings are consistent.
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_configdiff(discord_ctx, args)


def main() -> None:
    """Main entry point for the Discord bot."""
    if Config.TOKEN is None:
        raise ValueError("DISCORD_TOKEN environment variable not set")

    bot.run(Config.TOKEN)


if __name__ == "__main__":
    main()
