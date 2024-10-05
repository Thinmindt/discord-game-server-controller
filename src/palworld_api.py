import json
from typing import Any, Dict
import requests

from src.info_models import ServerInfo


class PalworldAPIError(Exception):
    """API command failed to send."""


class PalworldAPI:

    def __init__(self, username: str, password: str):
        self.headers = {
            "Accept": "application/json",
            "Content-type": "application/json",
        }
        self.auth = requests.auth.HTTPBasicAuth(username, password)

        self.base_url = "http://localhost:8212/v1/api/"

    def is_on(self):
        """Return True if the server is running and responding. Else, False."""

        try:
            info = self.get_server_info()
        except requests.RequestException:
            return False  # If the connection is refused, assume it's off.
        if info.servername:
            return True
        return False

    def send_get_request(
        self, url: str, payload: Dict[Any, Any] = {}
    ) -> Dict[Any, Any]:
        """Send a generic request to the server. Returns the response as a dict."""

        response = requests.request(
            "GET", url, headers=self.headers, data=payload, auth=self.auth
        )
        response_dict = json.loads(response.text)
        return response_dict

    def get_server_info(self) -> ServerInfo:
        """Return `ServerInfo` from Palworld server."""

        url = f"{self.base_url}info"

        response = self.send_get_request(url)
        info = ServerInfo(**response)

        return info

    def shutdown_server(self, wait_time: int):
        """Send a command to shut the server down. Returns True if the request sends successfully, else False.

        `wait_time` is the time until the server stops in seconds."""

        payload = {
            "waittime": wait_time,
            "message": f"The server will shut down in {wait_time} seconds",
        }
        url = f"{self.base_url}shutdown"

        response = requests.request(
            "POST", url, headers=self.headers, json=payload, auth=self.auth
        )
        if response.status_code != 200:
            raise PalworldAPIError(
                f"Failed to send shutdown request. Failed with error: {response.status_code}"
            )
