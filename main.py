import asyncio
import pathlib
import discord
from discord.ext import commands

import os

import discord
from dotenv import load_dotenv

from src.palworld_api import PalworldAPI
from src.server_conductor import ServerConductor

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_PATH = pathlib.Path(os.getenv("SERVER_PATH") or "")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
API_USERNAME = os.getenv("SERVER_REST_API_USERNAME")
API_PASSWORD = os.getenv("SERVER_REST_API_PASSWORD")

assert SERVER_PATH
assert TOKEN
assert API_USERNAME
assert API_PASSWORD

COMMAND_PREFIX = "!"

palworld_api = PalworldAPI(API_USERNAME, API_PASSWORD)
server_conductor: ServerConductor = ServerConductor(SERVER_PATH, palworld_api)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)


@bot.command(name="start")
async def start_server(ctx):
    """Start the game server."""

    if not server_conductor.is_on:
        server_conductor.start_server()
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
    if server_conductor.is_on:
        try:
            palworld_api.shutdown_server(wait_time=wait_time)
            await ctx.send(f"Server will shut down in {wait_time} seconds.")
        except Exception as error:
            await ctx.send(error)
    else:
        await ctx.send("Server is not running.")


bot.run(TOKEN)
