import pathlib
import subprocess
from typing import Optional

from src.server_monitor import ServerMonitor


class ServerControlError(Exception):
    """A command issued to the game server failed."""


class ServerConductor:
    """Control a Steam CMD style server. Initialize it with the path to the server executable."""

    def __init__(self, server_path: pathlib.Path):
        self.server_path = server_path
        self.server_process: Optional[subprocess.Popen] = None
        self.monitor: Optional[ServerMonitor] = None

    @property
    def is_on(self):
        """True if the server is running."""

        if self.server_process is None:
            return False

        # Check if the subprocess is alive
        poll = self.server_process.poll()
        if poll is None:
            # The subprocess is alive
            return True
        self.server_process = None
        return False

    def add_monitor(self, monitor: ServerMonitor):
        self.monitor = monitor
        self.monitor.start_monitoring(self.server_process)

    def kill_monitor(self):
        self.monitor.stop_monitoring()
        self.monitor = None

    def start_server(self):
        """Execute the server binary and keep it alive."""

        self.server_process = subprocess.Popen(
            [self.server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if self.monitor:
            self.monitor.start_monitoring(self.server_process)

    def stop_server(self):
        """If the server is running, stop it."""

        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
        else:
            raise ServerControlError("The server does not appear to be running.")

    def restart_server(self):
        """If the server is running, restart it."""

        self.stop_server()
        self.start_server()
