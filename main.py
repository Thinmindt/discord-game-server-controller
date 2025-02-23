import asyncio
import discord
from discord.ext import commands


import discord

from src.config import Config
from src.palworld_api import PalworldAPI
from src.server_conductor import ServerConductor, ServerControlError

COMMAND_PREFIX = "!"

# These interact with the game server
palworld_api = PalworldAPI(Config.API_USERNAME, Config.API_PASSWORD)
server_conductor: ServerConductor = ServerConductor(
    Config.SERVER_PATH, palworld_api, Config.STEAM_CMD_PATH
)

# These interact with Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

list_of_commands = ["help", "start", "restart", "stop", "update"]


@bot.command(name="start")
async def start_server(ctx):
    """Start the game server."""

    if not server_conductor.is_on:
        await ctx.send("Checking for updates before starting...")
        server_conductor.update_server()
        await ctx.send("Starting server...")
        server_conductor.start_server()
        while not server_conductor.is_on:
            asyncio.sleep(1)
        await ctx.send("Server started!")
    else:
        await ctx.send("Server is already running.")


@bot.command(name="restart")
async def restart_server(ctx):
    """Restart the game server."""

    wait_time = 10  # seconds from shutdown command issued until the server stops.
    if server_conductor.is_on:
        try:
            palworld_api.shutdown_server(wait_time=10)
            await ctx.send(
                f"Server shutting down in {wait_time} seconds to prepare for a reset. Log out now!"
            )
        except Exception as error:
            await ctx.send(error)
            return
        await asyncio.sleep(wait_time + 5)
        server_conductor.start_server()
        await ctx.send("Server restarted!")
    else:
        await ctx.send("Server is not running.")


@bot.command(name="stop")
async def stop_server(ctx):
    """Stop and close the game server."""

    wait_time = 10  # seconds
    extra_wait_allowance = 10  # give it an extra 10 seconds.
    if server_conductor.is_on:
        try:
            palworld_api.shutdown_server(wait_time=wait_time)
            await ctx.send(f"Server will shut down in {wait_time} seconds.")

            await asyncio.sleep(10)

            while server_conductor.is_on and extra_wait_allowance > 0:
                wait_interval = 2
                await asyncio.sleep(wait_interval)
                extra_wait_allowance -= wait_interval

            await ctx.send(f"The server is now off.")
        except Exception as error:
            await ctx.send(error)
    else:
        await ctx.send("Server is not running.")


@bot.command(name="update")
async def update_server(ctx):
    """Update the server. You must stop the server before updating."""

    if server_conductor.is_on:
        await ctx.send(f"The server is running. Shut it down before updating.")
        return

    await ctx.send(f"Starting update. Please wait...")

    try:
        server_conductor.update_server()

        await ctx.send(f"Server update executed successfully.")
    except ServerControlError as error:
        await ctx.send(f"Server update failed: {error}")


bot.run(Config.TOKEN)
