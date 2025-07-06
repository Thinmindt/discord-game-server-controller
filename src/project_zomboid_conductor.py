import os
import pathlib
import subprocess

from src.game_server_interface import (
    GameServerConductor,
    GameServerAPI,
    ServerControlError,
)


class ProjectZomboidServerConductor(GameServerConductor):
    """Control a Project Zomboid server."""

    def __init__(
        self,
        server_path: pathlib.Path,
        api: GameServerAPI,
        steam_cmd_path: pathlib.Path,
        server_name: str = "servertest",
        memory_gb: int = 4,
    ):
        super().__init__(server_path, api, steam_cmd_path)
        self.server_name = server_name
        self.memory_gb = memory_gb

    def start_server(self) -> None:
        """Execute the Project Zomboid server and keep it alive."""

        if os.name == "nt":  # Windows
            self._start_windows_server()
        else:  # Linux
            self._start_linux_server()

    def _start_windows_server(self) -> None:
        """Start Project Zomboid server on Windows."""
        # Find the StartServer64.bat file
        server_dir = self.server_path.parent if self.server_path.is_file() else self.server_path
        original_batch_file = server_dir / "StartServer64.bat"

        if not original_batch_file.exists():
            raise ServerControlError("Could not find Project Zomboid server batch file")

        # Get the batch file to use (original or modified)
        batch_file = self._modify_batch_file(original_batch_file)

        print(f"Starting Project Zomboid server with: {batch_file}")
        print("Server output will appear below:")
        print("-" * 50)

        # Start the server process without capturing output so we can see it in real-time
        self.server_process = subprocess.Popen(
            [str(batch_file)],
            cwd=str(server_dir),
            text=True,
        )

    def _start_linux_server(self) -> None:
        """Start Project Zomboid server on Linux."""
        server_dir = self.server_path.parent if self.server_path.is_file() else self.server_path
        start_script = server_dir / "start-server.sh"

        if not start_script.exists():
            raise ServerControlError("Could not find start-server.sh")

        start_cmd = ["bash", str(start_script), "-servername", self.server_name]

        print(f"Starting Project Zomboid server with command: {' '.join(start_cmd)}")
        print("Server output will appear below:")
        print("-" * 50)

        self.server_process = subprocess.Popen(
            start_cmd,
            cwd=str(server_dir),
            text=True,
        )

    def _modify_batch_file(self, batch_file: pathlib.Path) -> pathlib.Path:
        """
        Modify the Windows batch file to use custom server name if needed.
        Returns the path to the batch file to use (original or modified).
        """
        # If using default server name, use original batch file
        if self.server_name == "servertest":
            return batch_file

        # Check if custom batch file already exists
        custom_batch = batch_file.parent / f"StartServer64_{self.server_name}.bat"
        if custom_batch.exists():
            return custom_batch

        # Read the original batch file
        if not batch_file.exists():
            raise ServerControlError(f"Original batch file not found: {batch_file}")

        with open(batch_file, "r") as f:
            content = f.read()

        # Only modify the server name parameter in the GameServer command line
        # Look for the pattern: zombie.network.GameServer and add -servername after it
        if "zombie.network.GameServer" in content:
            # Replace zombie.network.GameServer with zombie.network.GameServer -servername NAME
            modified_content = content.replace(
                "zombie.network.GameServer",
                f"zombie.network.GameServer -servername {self.server_name}",
            )

            # Write the modified batch file
            with open(custom_batch, "w") as f:
                f.write(modified_content)

            return custom_batch
        else:
            raise ServerControlError(
                f"Could not find 'zombie.network.GameServer' in batch file: {batch_file}"
            )

    def update_server(self) -> None:
        """Update the Project Zomboid server using SteamCMD."""

        # Project Zomboid server app ID is 380870
        cmd = [
            str(self.steam_cmd_path),
            "+force_install_dir",
            str(self.server_path.parent),
            "+login",
            "anonymous",
            "+app_update",
            "380870",  # Project Zomboid Dedicated Server
            "validate",
            "+quit",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"SteamCMD output: {result.stdout}")
        except subprocess.CalledProcessError as error:
            if error.returncode == 10:
                print("Timeout... Please try again.")
            elif error.returncode == 134:
                print("SteamCMD error occurred. Try again.")

            raise ServerControlError(f"SteamCMD update failed with: {error}")

    def get_default_port(self) -> int:
        """Get the default port for Project Zomboid server."""
        return 16261
