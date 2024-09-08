import discord

import os

import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")


class CustomClient(discord.Client):
    async def on_ready(self):
        print(f"{self.user} has connected to Discord!")


intents = discord.Intents.default()
intents.message_content = True

client = CustomClient(intents=intents)
client.run(TOKEN)
