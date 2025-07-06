import discord
from discord.ext import commands
from typing import Optional

from src.config import Config
from src.game_commands import game_commands

COMMAND_PREFIX = "!"


class DiscordContext:
    """Adapter to make Discord context compatible with MessageContext protocol."""

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx

    async def send(self, message: str) -> None:
        """Send a message to Discord."""
        await self.ctx.send(message)


# These interact with Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)


@bot.command(name="start")
async def start_server(ctx: commands.Context, game_type: Optional[str] = None):
    """Start the game server.

    Usage: !start [game_type]
    Examples: !start pz, !start palworld, !start
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_start(discord_ctx, args)


@bot.command(name="restart")
async def restart_server(ctx: commands.Context, game_type: Optional[str] = None):
    """Restart the game server.

    Usage: !restart [game_type]
    Examples: !restart pz, !restart palworld, !restart
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_restart(discord_ctx, args)


@bot.command(name="stop")
async def stop_server(ctx: commands.Context, game_type: Optional[str] = None):
    """Stop and close the game server.

    Usage: !stop [game_type]
    Examples: !stop pz, !stop palworld, !stop
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_stop(discord_ctx, args)


@bot.command(name="update")
async def update_server(ctx: commands.Context, game_type: Optional[str] = None):
    """Update the server. You must stop the server before updating.

    Usage: !update [game_type]
    Examples: !update pz, !update palworld, !update
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_update(discord_ctx, args)


@bot.command(name="info")
async def get_info(ctx: commands.Context, game_type: Optional[str] = None):
    """Display information about the running server.

    Usage: !info [game_type]
    Examples: !info pz, !info palworld, !info
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_info(discord_ctx, args)


@bot.command(name="ip")
async def get_ip(ctx: commands.Context, game_type: Optional[str] = None):
    """Display the public IP address of the host.

    Usage: !ip [game_type]
    Examples: !ip pz, !ip palworld, !ip
    """
    args = [game_type] if game_type else []
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_ip(discord_ctx, args)


@bot.command(name="games")
async def list_games(ctx: commands.Context):
    """List all supported game types and their aliases."""
    discord_ctx = DiscordContext(ctx)
    await game_commands.cmd_games(discord_ctx, [])


def main():
    """Main entry point for the Discord bot."""
    if Config.TOKEN is None:
        raise ValueError("DISCORD_TOKEN environment variable not set")

    bot.run(Config.TOKEN)


if __name__ == "__main__":
    main()
