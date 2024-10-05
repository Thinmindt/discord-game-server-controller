import pathlib
import subprocess
from typing import Optional

from src.palworld_api import PalworldAPI


class ServerControlError(Exception):
    """A command issued to the game server failed."""


class ServerConductor:
    """Control a Steam CMD style server. Initialize it with the path to the server executable."""

    def __init__(self, server_path: pathlib.Path, api: PalworldAPI):
        self.server_path = server_path
        self.api = api

    @property
    def is_on(self):
        """True if the server is running."""

        return self.api.is_on()

    def start_server(self):
        """Execute the server binary and keep it alive."""

        self.server_process = subprocess.Popen(
            [self.server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
