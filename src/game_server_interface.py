import pathlib
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.backup_manager import BackupResult


@dataclass
class ServerInfo:
    """Common server information structure for all game types."""

    server_name: str
    version: str
    description: str
    max_players: int | None = None
    current_players: int | None = None
    uptime: str | None = None
    additional_info: dict[str, Any] | None = None


class GameServerManager(ABC):
    """
    Unified interface for managing game servers.

    This interface combines server control (starting, stopping, updating)
    with server monitoring (status, info) in a single class.

    Different games can implement this interface in different ways:
    - API-based games (like Palworld) can use REST API calls for monitoring
    - Log-based games (like Project Zomboid) can parse logs and use process monitoring
    """

    def __init__(self, server_path: pathlib.Path, steam_cmd_path: pathlib.Path):
        self.server_path = server_path
        self.steam_cmd_path = steam_cmd_path

    @abstractmethod
    def is_on(self) -> bool:
        """Return True if the server is running and responding. Else, False."""
        pass

    @abstractmethod
    def get_server_info(self) -> ServerInfo:
        """Return ServerInfo from the game server."""
        pass

    @abstractmethod
    def start_server(self) -> None:
        """Execute the server binary and keep it alive."""
        pass

    @abstractmethod
    def shutdown_server(self, wait_time: int = 30) -> None:
        """
        Shut down the server.

        Args:
            wait_time: Time to wait for graceful shutdown before force killing (seconds).
        """
        pass

    @abstractmethod
    def update_server(self) -> None:
        """Update the server using SteamCMD."""
        pass

    @abstractmethod
    def get_default_port(self) -> int:
        """Get the default port for this game server."""
        pass

    def send_server_command(self, command: str) -> str:
        """
        Send a command to the running game server.

        Args:
            command: The command to send to the server

        Returns:
            A message indicating the result of the command

        Raises:
            ServerControlError: If the server doesn't support commands or command fails
        """
        raise ServerControlError("This game server does not support ad-hoc commands")

    def backup_server(self, progress_callback: Callable[[str], None] | None = None) -> BackupResult:
        """
        Create a backup of the server data.

        Args:
            progress_callback: Optional callback function that receives progress messages

        Returns:
            BackupResult with success status, backup path, and list of files backed up

        Raises:
            ServerControlError: If backup is not supported or fails
        """
        raise ServerControlError("This game server does not support backups")

    def get_backup_paths(self) -> dict[str, pathlib.Path]:
        """
        Get the paths that would be backed up.

        Returns:
            Dictionary mapping backup item names to their paths

        Raises:
            ServerControlError: If backup is not supported
        """
        raise ServerControlError("This game server does not support backups")

    def get_version(self) -> dict[str, str]:
        """
        Get the current version/branch information for the server.

        Returns:
            Dictionary with 'branch' (stable/beta) and 'version' (build number if known)

        Raises:
            ServerControlError: If version detection is not supported
        """
        raise ServerControlError("This game server does not support version detection")

    def set_version(self, branch: str) -> str:
        """
        Switch the server to a different version/branch.

        Args:
            branch: The branch to switch to (e.g., 'stable', 'beta')

        Returns:
            A message describing the result of the operation

        Raises:
            ServerControlError: If version switching is not supported or fails
        """
        raise ServerControlError("This game server does not support version switching")

    def get_available_versions(self) -> list[dict[str, str | bool]]:
        """
        Get the list of available versions/branches for this server.

        Returns:
            List of dictionaries with 'id', 'name', and 'description' for each version

        Raises:
            ServerControlError: If version listing is not supported
        """
        raise ServerControlError("This game server does not support version listing")


class ServerControlError(Exception):
    """A command issued to the game server failed."""

    pass
