import os
import pathlib
from dotenv import load_dotenv
import requests


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

    def get_public_ip():
        try:
            response = requests.get("https://api.ipify.org")
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None
