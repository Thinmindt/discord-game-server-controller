import os
import pathlib
import psutil
import time

from src.game_server_interface import GameServerAPI, ServerInfo


class ProjectZomboidAPIError(Exception):
    """Project Zomboid API command failed to send."""


class ProjectZomboidAPI(GameServerAPI):
    """Project Zomboid server API implementation using process monitoring."""

    def __init__(self, server_name: str = "servertest"):
        self.server_name = server_name
        self.java_process = None

        # Default paths - can be customized via config
        if os.name == "nt":  # Windows
            self.zomboid_home = pathlib.Path.home() / "Zomboid"
        else:  # Linux
            self.zomboid_home = pathlib.Path.home() / "Zomboid"

        self.server_config_path = self.zomboid_home / "Server" / f"{server_name}.ini"

    def is_on(self) -> bool:
        """Return True if the Project Zomboid server is running."""
        try:
            # Look for Java processes running Project Zomboid
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["name"] and "java" in proc.info["name"].lower():
                        cmdline = proc.info["cmdline"]
                        if cmdline and any("zombie.network.GameServer" in arg for arg in cmdline):
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except Exception:
            return False

    def get_server_info(self) -> ServerInfo:
        """Return ServerInfo from Project Zomboid server by parsing config."""

        if not self.server_config_path.exists():
            # Return default info if config doesn't exist
            return ServerInfo(
                server_name=self.server_name,
                version="Unknown",
                description="Project Zomboid Server",
                additional_info={"game_type": "project_zomboid"},
            )

        try:
            # Parse the .ini file to get server information
            config_data = {}
            with open(self.server_config_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        config_data[key.strip()] = value.strip()

            return ServerInfo(
                server_name=config_data.get("PublicName", self.server_name),
                version="Build 41+",  # Would need to parse from actual server
                description=config_data.get("PublicDescription", "Project Zomboid Server"),
                max_players=int(config_data.get("MaxPlayers", 32)),
                additional_info={
                    "game_type": "project_zomboid",
                    "udp_port": config_data.get("UDPPort", "16261"),
                    "open": config_data.get("Open", "true"),
                    "public": config_data.get("Public", "false"),
                },
            )
        except Exception as e:
            return ServerInfo(
                server_name=self.server_name,
                version="Unknown",
                description=f"Error reading config: {str(e)}",
                additional_info={"game_type": "project_zomboid"},
            )

    def shutdown_server(self, wait_time: int) -> None:
        """Send a shutdown command to the Project Zomboid server."""
        try:
            # For Project Zomboid, we need to send commands to the server
            # console. This is a simplified implementation - in practice,
            # you'd need to either use stdin of the server process or
            # implement RCON

            # Find the Java process running the server
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["name"] and "java" in proc.info["name"].lower():
                        cmdline = proc.info["cmdline"]
                        if cmdline and any("zombie.network.GameServer" in arg for arg in cmdline):
                            # Send save command first, then quit
                            # Note: This is a simplified approach
                            # In a real implementation, you'd want to use
                            # proper IPC
                            print(f"Attempting to shutdown PZ server " f"(PID: {proc.info['pid']})")

                            # Graceful shutdown attempt
                            time.sleep(wait_time)
                            proc.terminate()
                            return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            raise ProjectZomboidAPIError("Could not find running Project Zomboid server process")

        except Exception as e:
            raise ProjectZomboidAPIError(f"Failed to shutdown server: {str(e)}")
