import pathlib
import subprocess
import requests
import json
from typing import Any, Dict, Optional

from src.game_server_interface import GameServerManager, ServerInfo, ServerControlError


class PalworldAPIError(Exception):
    """API command failed to send."""


class PalworldServerManager(GameServerManager):
    """Unified Palworld server manager with REST API monitoring."""

    def __init__(
        self,
        server_path: pathlib.Path,
        steam_cmd_path: pathlib.Path,
        username: str,
        password: str,
        host: str = "localhost",
        port: int = 8212,
    ):
        super().__init__(server_path, steam_cmd_path)
        self.username = username
        self.password = password
        self.host = host
        self.port = port

        self.headers = {
            "Accept": "application/json",
            "Content-type": "application/json",
        }
        self.auth = requests.auth.HTTPBasicAuth(username, password)
        self.base_url = f"http://{host}:{port}/v1/api/"
        self.server_process: Optional[subprocess.Popen] = None

    def is_on(self) -> bool:
        """Return True if the server is running and responding via API."""
        try:
            info = self.get_server_info()
            return bool(info.server_name)
        except (requests.RequestException, ServerControlError):
            return False

    def get_server_info(self) -> ServerInfo:
        """Return ServerInfo from Palworld server via REST API."""
        url = f"{self.base_url}info"

        try:
            response = self._send_get_request(url)
        except requests.RequestException as e:
            raise ServerControlError(f"Failed to get server info: {e}")

        # Convert Palworld-specific response to common ServerInfo format
        info = ServerInfo(
            server_name=response.get("servername", ""),
            version=response.get("version", "Unknown"),
            description=response.get("description", ""),
        )

        return info

    def start_server(self) -> None:
        """Execute the Palworld server and keep it alive."""
        if self.is_on():
            raise ServerControlError("Server is already running")

        print(f"Starting Palworld server: {self.server_path}")
        print("Server output will appear below:")
        print("-" * 50)

        # Start the server process
        self.server_process = subprocess.Popen(
            [str(self.server_path), "-publiclobby"],
            text=True,
        )

        print("🎉 Palworld server process started!")
        print("Note: It may take a few minutes for the REST API to become available.")

    def shutdown_server(self, wait_time: int = 30) -> None:
        """
        Shut down the Palworld server via API command or process termination.

        Args:
            wait_time: Time to wait for graceful shutdown before force killing (seconds).
        """
        # Try graceful API shutdown first if server is responding
        if self.is_on():
            try:
                self._shutdown_via_api(wait_time)
                return
            except (requests.RequestException, ServerControlError) as e:
                print(f"API shutdown failed: {e}, falling back to process termination...")

        # Fall back to process termination
        if self.server_process:
            print("Shutting down Palworld server via process termination...")

            self.server_process.terminate()

            try:
                self.server_process.wait(timeout=wait_time)
                print("Server shut down gracefully")
            except subprocess.TimeoutExpired:
                print(f"Graceful shutdown timed out after {wait_time}s, force killing...")
                self.server_process.kill()
                self.server_process.wait()
                print("Server force killed")

            self.server_process = None
        else:
            raise ServerControlError("No server process to shut down and API shutdown failed")

    def _shutdown_via_api(self, wait_time: int) -> None:
        """Shut down server via REST API."""
        url = f"{self.base_url}shutdown"
        payload = {
            "waittime": wait_time,
            "message": "Server shutting down via Discord bot",
        }

        try:
            response = self._send_post_request(url, payload)
            if response.get("raw_response"):
                msg = response.get("message", "")
                print(f"Server shutdown initiated via API (raw response): {msg}")
            else:
                print(f"Server shutdown initiated via API: {response}")
        except requests.RequestException as e:
            raise ServerControlError(f"Failed to shutdown server via API: {e}")

    def update_server(self) -> None:
        """Update the Palworld server using SteamCMD."""
        if self.is_on():
            raise ServerControlError("Cannot update server while it's running. Stop it first.")

        # Palworld server app ID is 2394010
        cmd = [
            str(self.steam_cmd_path),
            "+force_install_dir",
            str(self.server_path.parent),
            "+login",
            "anonymous",
            "+app_update",
            "2394010",  # Palworld Dedicated Server
            "validate",
            "+quit",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"SteamCMD output: {result.stdout}")
        except subprocess.CalledProcessError as error:
            raise ServerControlError(f"SteamCMD update failed: {error}")

    def get_default_port(self) -> int:
        """Get the default port for Palworld server."""
        return 8211

    def _send_get_request(self, url: str, payload: Dict[Any, Any] = {}) -> Dict[str, Any]:
        """Send a GET request to the server. Returns the response as a dict."""
        response = requests.request("GET", url, headers=self.headers, data=payload, auth=self.auth)
        response.raise_for_status()

        # Handle empty responses or non-JSON responses
        if not response.text.strip():
            return {"status": "success", "message": "Request completed (empty response)"}

        try:
            response_dict: Dict[str, Any] = json.loads(response.text)
            return response_dict
        except json.JSONDecodeError:
            # If it's not JSON, return the text as a message
            return {"status": "success", "message": response.text, "raw_response": True}

    def _send_post_request(self, url: str, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """Send a POST request to the server. Returns the response as a dict."""
        response = requests.post(url, headers=self.headers, json=payload, auth=self.auth)
        response.raise_for_status()

        # Handle empty responses or non-JSON responses
        if not response.text.strip():
            return {"status": "success", "message": "Request completed (empty response)"}

        try:
            response_dict: Dict[str, Any] = json.loads(response.text)
            return response_dict
        except json.JSONDecodeError:
            # If it's not JSON, return the text as a message
            return {"status": "success", "message": response.text, "raw_response": True}

    # Additional Palworld-specific methods
    def get_players(self) -> Dict[str, Any]:
        """Get list of players currently on the server."""
        url = f"{self.base_url}players"
        return self._send_get_request(url)

    def kick_player(self, steam_id: str, message: str = "You have been kicked") -> Dict[str, Any]:
        """Kick a player from the server."""
        url = f"{self.base_url}kick"
        payload = {"userid": steam_id, "message": message}
        return self._send_post_request(url, payload)

    def ban_player(self, steam_id: str, message: str = "You have been banned") -> Dict[str, Any]:
        """Ban a player from the server."""
        url = f"{self.base_url}ban"
        payload = {"userid": steam_id, "message": message}
        return self._send_post_request(url, payload)

    def broadcast_message(self, message: str) -> Dict[str, Any]:
        """Broadcast a message to all players."""
        url = f"{self.base_url}announce"
        payload = {"message": message}
        return self._send_post_request(url, payload)
