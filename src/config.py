import os
import pathlib
from dotenv import load_dotenv


class Config:
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    SERVER_PATH = pathlib.Path(os.getenv("SERVER_PATH") or "")
    STEAM_CMD_PATH = pathlib.Path(os.getenv("STEAM_CMD_PATH") or "")
    DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
    API_USERNAME = os.getenv("SERVER_REST_API_USERNAME")
    API_PASSWORD = os.getenv("SERVER_REST_API_PASSWORD")

    assert SERVER_PATH
    assert TOKEN
    assert API_USERNAME
    assert API_PASSWORD
