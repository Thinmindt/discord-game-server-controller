from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
import pathlib


@dataclass
class ServerInfo:
    """Common server information structure for all game types."""

    server_name: str
    version: str
    description: str
    max_players: Optional[int] = None
    current_players: Optional[int] = None
    uptime: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


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


class ServerControlError(Exception):
    """A command issued to the game server failed."""

    pass
