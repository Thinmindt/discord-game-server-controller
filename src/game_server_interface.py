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


class GameServerAPI(ABC):
    """Abstract base class for game server APIs."""

    @abstractmethod
    def is_on(self) -> bool:
        """Return True if the server is running and responding. Else, False."""
        pass

    @abstractmethod
    def get_server_info(self) -> ServerInfo:
        """Return ServerInfo from the game server."""
        pass

    @abstractmethod
    def shutdown_server(self, wait_time: int) -> None:
        """Send a command to shut the server down.

        Args:
            wait_time: Time until the server stops in seconds.
        """
        pass


class GameServerConductor(ABC):
    """Abstract base class for game server conductors."""

    def __init__(
        self,
        server_path: pathlib.Path,
        api: GameServerAPI,
        steam_cmd_path: pathlib.Path,
    ):
        self.server_path = server_path
        self.steam_cmd_path = steam_cmd_path
        self.api = api

    @property
    def is_on(self) -> bool:
        """True if the server is running."""
        return self.api.is_on()

    @abstractmethod
    def start_server(self) -> None:
        """Execute the server binary and keep it alive."""
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
