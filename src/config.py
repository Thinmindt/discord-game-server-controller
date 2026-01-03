import os
import pathlib
from dotenv import load_dotenv
import requests


class Config:
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")

    # Palworld specific configs
    PALWORLD_SERVER_PATH = pathlib.Path(os.getenv("PALWORLD_SERVER_PATH") or "")
    PALWORLD_API_USERNAME = os.getenv("PALWORLD_SERVER_REST_API_USERNAME")
    PALWORLD_API_PASSWORD = os.getenv("PALWORLD_SERVER_REST_API_PASSWORD")

    # Project Zomboid specific configs
    PZ_SERVER_PATH = pathlib.Path(os.getenv("PZ_SERVER_PATH") or os.getenv("SERVER_PATH") or "")
    PZ_SERVER_NAME = os.getenv("PZ_SERVER_NAME", "servertest")
    PZ_MEMORY_GB = int(os.getenv("PZ_MEMORY_GB", "4"))
    PZ_BACKUP_PATH = pathlib.Path(os.getenv("PZ_BACKUP_PATH") or "D:\\ZomboidServerBackup")

    # Common configs
    STEAM_CMD_PATH = pathlib.Path(os.getenv("STEAM_CMD_PATH") or "")
    DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
    DEFAULT_GAME = os.getenv("DEFAULT_GAME", "palworld")

    assert TOKEN
    # Only assert Palworld configs if we're using Palworld
    if DEFAULT_GAME.lower() in ["palworld", "pal"]:
        assert PALWORLD_SERVER_PATH
        assert PALWORLD_API_USERNAME
        assert PALWORLD_API_PASSWORD

    @staticmethod
    def get_public_ip():
        try:
            response = requests.get("https://api.ipify.org")
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None
