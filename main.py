import pathlib
import discord
from discord.ext import commands

import os

import discord
from dotenv import load_dotenv

from src.server_conductor import ServerConductor
from src.server_monitor import ServerMonitor

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_PATH = pathlib.Path(os.getenv("SERVER_PATH") or "")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

if not SERVER_PATH.exists():
    raise Exception(
        "ERROR: The path for the server in your `.env` file does not exist."
    )
if TOKEN is None:
    raise Exception("ERROR: Discord token was not found")

COMMAND_PREFIX = "!"

server_conductor: ServerConductor = ServerConductor(SERVER_PATH)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)


@bot.command(name="start")
async def start_server(ctx):
    """Start the game server."""

    if not server_conductor.is_on:
        server_conductor.start_server()
        await ctx.send("Server started!")
        server_monitor = ServerMonitor(DISCORD_CHANNEL_ID, bot)
        server_conductor.add_monitor(server_monitor)
    else:
        await ctx.send("Server is already running.")


@bot.command(name="restart")
async def restart_server(ctx):
    """Restart the game server."""

    if server_conductor.is_on:
        server_conductor.restart_server()
        await ctx.send("Server restarted!")
    else:
        await ctx.send("Server is not running.")


bot.run(TOKEN)
