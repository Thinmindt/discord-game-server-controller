import asyncio
import discord
from discord.ext import commands
from typing import Dict, Tuple, Optional

from src.config import Config
from src.game_server_interface import (
    GameServerAPI,
    GameServerConductor,
    ServerControlError,
)
from src.server_factory import ServerFactory

COMMAND_PREFIX = "!"

# Cache for server instances to avoid recreating them
server_instances: Dict[str, Tuple[GameServerAPI, GameServerConductor]] = {}


def get_server_instance(game_type: str) -> Tuple[GameServerAPI, GameServerConductor]:
    """Get or create server instances for the specified game type."""
    game_type = game_type.lower()

    if game_type not in server_instances:
        server_instances[game_type] = ServerFactory.create_server_instances(game_type)

    return server_instances[game_type]


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

    if game_type is None:
        game_type = Config.DEFAULT_GAME

    if not ServerFactory.is_supported_game(game_type):
        supported = ", ".join(ServerFactory.get_supported_games().keys())
        await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
        return

    try:
        api, server_conductor = get_server_instance(game_type)
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


@bot.command(name="restart")
async def restart_server(ctx, game_type: Optional[str] = None):
    """Restart the game server.

    Usage: !restart [game_type]
    Examples: !restart pz, !restart palworld, !restart
    """

    if game_type is None:
        game_type = Config.DEFAULT_GAME

    if not ServerFactory.is_supported_game(game_type):
        supported = ", ".join(ServerFactory.get_supported_games().keys())
        await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
        return

    try:
        api, server_conductor = get_server_instance(game_type)
        game_name = ServerFactory.get_supported_games()[game_type.lower()]
    except ValueError as e:
        await ctx.send(f"Error: {str(e)}")
        return

    wait_time = 10  # seconds from shutdown command issued until the server stops.
    if server_conductor.is_on:
        try:
            api.shutdown_server(wait_time=10)
            await ctx.send(
                f"{game_name} server shutting down in {wait_time} seconds to prepare for a reset. "
                f"Log out now!"
            )
        except Exception as error:
            await ctx.send(f"Error during shutdown: {error}")
            return
        await asyncio.sleep(wait_time + 5)
        server_conductor.start_server()
        await ctx.send(f"{game_name} server restarted!")
    else:
        await ctx.send(f"{game_name} server is not running.")


@bot.command(name="stop")
async def stop_server(ctx, game_type: Optional[str] = None):
    """Stop and close the game server.

    Usage: !stop [game_type]
    Examples: !stop pz, !stop palworld, !stop
    """

    if game_type is None:
        game_type = Config.DEFAULT_GAME

    if not ServerFactory.is_supported_game(game_type):
        supported = ", ".join(ServerFactory.get_supported_games().keys())
        await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
        return

    try:
        api, server_conductor = get_server_instance(game_type)
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


@bot.command(name="update")
async def update_server(ctx, game_type: Optional[str] = None):
    """Update the server. You must stop the server before updating.

    Usage: !update [game_type]
    Examples: !update pz, !update palworld, !update
    """

    if game_type is None:
        game_type = Config.DEFAULT_GAME

    if not ServerFactory.is_supported_game(game_type):
        supported = ", ".join(ServerFactory.get_supported_games().keys())
        await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
        return

    try:
        api, server_conductor = get_server_instance(game_type)
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


@bot.command(name="info")
async def get_info(ctx, game_type: Optional[str] = None):
    """Display information about the running server.

    Usage: !info [game_type]
    Examples: !info pz, !info palworld, !info
    """

    if game_type is None:
        game_type = Config.DEFAULT_GAME

    if not ServerFactory.is_supported_game(game_type):
        supported = ", ".join(ServerFactory.get_supported_games().keys())
        await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
        return

    try:
        api, server_conductor = get_server_instance(game_type)
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


@bot.command(name="ip")
async def get_ip(ctx, game_type: Optional[str] = None):
    """Display the public IP address of the host.

    Usage: !ip [game_type]
    Examples: !ip pz, !ip palworld, !ip
    """

    if game_type is None:
        game_type = Config.DEFAULT_GAME

    if not ServerFactory.is_supported_game(game_type):
        supported = ", ".join(ServerFactory.get_supported_games().keys())
        await ctx.send(f"Unsupported game type '{game_type}'. Supported games: {supported}")
        return

    try:
        api, server_conductor = get_server_instance(game_type)
        game_name = ServerFactory.get_supported_games()[game_type.lower()]
        port = server_conductor.get_default_port()
    except ValueError as e:
        await ctx.send(f"Error: {str(e)}")
        return

    ip = Config.get_public_ip()
    await ctx.send(f"The {game_name} server host IP address is: {ip}:{port}")


@bot.command(name="games")
async def list_games(ctx):
    """List all supported game types and their aliases."""

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
        "Supported games:\n" + "\n".join(game_list) + f"\n\nDefault game: `{Config.DEFAULT_GAME}`"
    )


bot.run(Config.TOKEN)
