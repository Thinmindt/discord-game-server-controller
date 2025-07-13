import os
import pathlib
import subprocess
import threading
from typing import Optional, List

from src.game_server_interface import (
    GameServerManager,
    ServerInfo,
    ServerControlError,
)


class ProjectZomboidServerManager(GameServerManager):
    """Unified Project Zomboid server manager with log-based monitoring."""

    def __init__(
        self,
        server_path: pathlib.Path,
        steam_cmd_path: pathlib.Path,
        server_name: str = "servertest",
        memory_gb: int = 4,
    ):
        super().__init__(server_path, steam_cmd_path)
        self.server_name = server_name
        self.memory_gb = memory_gb
        self.server_process: Optional[subprocess.Popen] = None
        self._server_started = False
        self._server_info: Optional[ServerInfo] = None
        self._log_lines: List[str] = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = False

    def is_on(self) -> bool:
        """Return True if the server process is running and has started successfully."""
        if not self.server_process:
            return False

        # Check if process is still running
        if self.server_process.poll() is not None:
            return False

        # Check if server has actually started (based on log parsing)
        return self._server_started

    def get_server_info(self) -> ServerInfo:
        """Return ServerInfo parsed from server logs."""
        if not self.is_on():
            raise ServerControlError("Server is not running")

        if self._server_info:
            return self._server_info

        # Parse basic info from logs
        server_info = ServerInfo(
            server_name=self.server_name,
            version="Build 41+",  # Could be parsed from logs
            description="Project Zomboid Dedicated Server",
        )

        # Parse additional info from recent log lines
        additional_info = {}
        for line in self._log_lines[-50:]:  # Check last 50 lines
            if "Server is listening on port" in line:
                # Extract port info
                if "port 16261" in line and "port 16262" in line:
                    additional_info = {"steam_port": 16261, "udp_port": 16262, "status": "Running"}
                    break
            elif "port 16261" in line or "port 16262" in line:
                # Fallback for different log formats
                additional_info = {"steam_port": 16261, "udp_port": 16262, "status": "Running"}
                break

        server_info.additional_info = additional_info if additional_info else None
        self._server_info = server_info
        return server_info

    def start_server(self) -> None:
        """Execute the Project Zomboid server and monitor its output."""
        if self.is_on():
            raise ServerControlError("Server is already running")

        if os.name == "nt":  # Windows
            self._start_windows_server()
        else:  # Linux
            self._start_linux_server()

        # Start monitoring thread to parse logs
        self._stop_monitoring = False
        self._monitor_thread = threading.Thread(target=self._monitor_server_output)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()

    def _start_windows_server(self) -> None:
        """Start Project Zomboid server on Windows."""
        server_dir = self.server_path.parent if self.server_path.is_file() else self.server_path
        original_batch_file = server_dir / "StartServer64.bat"

        if not original_batch_file.exists():
            raise ServerControlError("Could not find Project Zomboid server batch file")

        # Get the batch file to use (original or modified)
        batch_file = self._modify_batch_file(original_batch_file)

        print(f"Starting Project Zomboid server with: {batch_file}")
        print("Server output will appear below:")
        print("-" * 50)

        # Start the server process with input/output capture for monitoring
        self.server_process = subprocess.Popen(
            [str(batch_file)],
            cwd=str(server_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1,
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
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def _monitor_server_output(self) -> None:
        """Monitor server output in a separate thread to detect startup and parse logs."""
        if not self.server_process or not self.server_process.stdout:
            return

        try:
            for line in iter(self.server_process.stdout.readline, ""):
                if self._stop_monitoring:
                    break

                line = line.strip()
                if not line:
                    continue

                # Print output in real-time
                print(line)

                # Store recent log lines
                self._log_lines.append(line)
                # Keep only last 100 lines to avoid memory issues
                if len(self._log_lines) > 100:
                    self._log_lines.pop(0)

                # Check for server startup completion
                if "*** SERVER STARTED ****" in line:
                    self._server_started = True
                    print("\n🎉 Project Zomboid server has started successfully!")
                    print("-" * 50)

                # Check for shutdown messages
                elif "Saving world" in line or "Server shutdown" in line or "Goodbye" in line:
                    print(f"🛑 {line}")

                # Check for port information
                elif "Server is listening on port" in line:
                    print(f"📡 {line}")

                # Check for client connection info
                elif "Clients should use" in line:
                    print(f"🔗 {line}")

        except Exception as e:
            print(f"Error monitoring server output: {e}")
        finally:
            if self.server_process and self.server_process.stdout:
                self.server_process.stdout.close()

    def shutdown_server(self, wait_time: int = 30) -> None:
        """Shut down the server gracefully using the quit command."""
        if not self.server_process:
            raise ServerControlError("No server process to shut down")

        print("Shutting down Project Zomboid server...")

        # Stop monitoring
        self._stop_monitoring = True

        # Send graceful shutdown command to the server
        try:
            # For Project Zomboid, we can send 'quit' command to stdin
            if self.server_process.stdin:
                print("Sending 'quit' command to server...")
                self.server_process.stdin.write("quit\n")
                self.server_process.stdin.flush()
                # Close stdin to signal end of input
                self.server_process.stdin.close()

            # Wait for graceful shutdown
            self.server_process.wait(timeout=wait_time)
            print("Server shut down gracefully")

        except subprocess.TimeoutExpired:
            print(f"Graceful shutdown timed out after {wait_time}s, terminating process...")
            self.server_process.terminate()

            try:
                self.server_process.wait(timeout=10)
                print("Server terminated")
            except subprocess.TimeoutExpired:
                # Force kill as last resort
                print("Force killing server process...")
                self.server_process.kill()
                self.server_process.wait()
                print("Server force killed")

        except Exception as e:
            print(f"Error during shutdown: {e}, falling back to process termination...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=10)
                print("Server terminated")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()
                print("Server force killed")

        self.server_process = None
        self._server_started = False
        self._server_info = None

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
        if self.is_on():
            raise ServerControlError("Cannot update server while it's running. Stop it first.")

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
