import pathlib
import subprocess

from src.config import Config
from src.game_server_interface import (
    GameServerConductor,
    GameServerAPI,
    ServerControlError,
)


class PalworldServerConductor(GameServerConductor):
    """Control a Palworld Steam CMD style server."""

    def __init__(
        self,
        server_path: pathlib.Path,
        api: GameServerAPI,
        steam_cmd_path: pathlib.Path,
    ):
        super().__init__(server_path, api, steam_cmd_path)

    def start_server(self):
        """Execute the server binary and keep it alive."""

        start_cmd = [
            str(self.server_path),
            "-publiclobby",
            f"publicip={Config.get_public_ip()}",
            "publicport=8211",
        ]
        print(f"Starting server with command: \n    {' '.join(start_cmd)}")
        self.server_process = subprocess.Popen(
            start_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def update_server(self) -> None:

        cmd = [
            str(self.steam_cmd_path),
            "+force_install_dir",
            "/home/Steam/steamapps/common/PalServer",
            "+login",
            "anonymous",
            "+app_update",
            "2394010",
            "validate",
            "+quit",
        ]
        try:
            self.server_process = subprocess.check_call(
                " ".join(cmd),
                shell=True,
            )
        except subprocess.CalledProcessError as error:
            if error.returncode == 10:
                print("Timout... Please try again.")
            elif error.returncode == 134:
                print("SteamCMD error occurred. Try again.")

            raise ServerControlError(f"SteamCMD update failed with: {error}")

    def get_default_port(self) -> int:
        """Get the default port for Palworld server."""
        return 8211
