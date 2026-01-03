import logging
import os
import pathlib
import subprocess
import threading
import time
from typing import Callable, Dict, Optional, List

from src.backup_manager import BackupResult, BackupUtility
from src.game_server_interface import (
    GameServerManager,
    ServerInfo,
    ServerControlError,
)
from src.config import Config


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
        self._log_lines_lock = threading.Lock()  # Add thread safety for log lines
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

                # Store recent log lines with thread safety
                with self._log_lines_lock:
                    self._log_lines.append(line)
                    # Keep only last 100 lines to avoid memory issues
                    if len(self._log_lines) > 100:
                        self._log_lines.pop(0)

                # Additional debug for command-related output
                if "command entered via server console" in line or "User " in line:
                    print(f"DEBUG MONITOR: Command-related line captured: {line}")

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

    def send_server_command(self, command: str) -> str:
        """
        Send a command to the running Project Zomboid server.

        Args:
            command: The admin command to send to the server

        Returns:
            A message indicating the result of the command

        Raises:
            ServerControlError: If the server is not running or command fails
        """
        if not self.is_on():
            raise ServerControlError("Cannot send command: Server is not running")

        if not self.server_process or not self.server_process.stdin:
            raise ServerControlError("Cannot send command: No stdin connection to server")

        try:
            # Store marker for tracking new output - use timestamp-based approach
            with self._log_lines_lock:
                # Get the last few lines to use as a marker
                if self._log_lines:
                    marker_lines = self._log_lines[-2:]  # Use last 2 lines as marker
                else:
                    marker_lines = []
                buffer_size_before = len(self._log_lines)
                last_few_lines = self._log_lines[-3:] if self._log_lines else []

            print(f"DEBUG: Initial buffer size: {buffer_size_before}")
            print(f"DEBUG: Process alive: {self.server_process.poll() is None}")
            print(
                f"DEBUG: Monitor thread alive: {self._monitor_thread.is_alive() if self._monitor_thread else False}"
            )
            print(f"DEBUG: Marker lines: {marker_lines}")

            # Send the command to the server
            command_to_send = f"{command}\n"
            print(f"Sending command to server: {command}")
            self.server_process.stdin.write(command_to_send)
            self.server_process.stdin.flush()
            print(f"DEBUG: Command sent and flushed successfully")

            # Wait for the server to process the command and generate output
            max_wait_time = 5.0  # Maximum time to wait for output
            check_interval = 0.1  # Check every 100ms
            waited_time = 0.0
            new_lines_found = []

            # Keep checking for new output until we get some or timeout
            while waited_time < max_wait_time:
                time.sleep(check_interval)
                waited_time += check_interval

                # Check for new lines after the marker position
                with self._log_lines_lock:
                    current_buffer = self._log_lines.copy()
                    recent_lines = self._log_lines[-5:] if self._log_lines else []

                # Find new lines that appeared after our marker
                new_lines_found = []
                if marker_lines:
                    # Find the position of our marker
                    marker_found = False
                    for i, line in enumerate(current_buffer):
                        if not marker_found:
                            # Look for the last marker line
                            if line == marker_lines[-1]:
                                marker_found = True
                                # Collect everything after the marker
                                new_lines_found = current_buffer[i + 1 :]
                                break
                else:
                    # No marker (empty buffer before), so everything is new
                    new_lines_found = current_buffer

                if waited_time % 1.0 < check_interval:  # Debug every second
                    print(f"DEBUG: After {waited_time:.1f}s - New logs: {len(new_lines_found)}")

                if new_lines_found:
                    # We got some output, wait a bit more to capture any additional lines
                    print(
                        f"DEBUG: Found {len(new_lines_found)} new log lines, waiting 0.5s more..."
                    )
                    print(f"DEBUG: New content: {new_lines_found}")
                    time.sleep(0.5)  # Give time for additional output
                    # Re-check for any additional lines after the wait
                    with self._log_lines_lock:
                        final_buffer = self._log_lines.copy()
                    # Get final new lines after marker
                    final_new_lines = []
                    if marker_lines:
                        marker_found = False
                        for i, line in enumerate(final_buffer):
                            if not marker_found:
                                if line == marker_lines[-1]:
                                    marker_found = True
                                    final_new_lines = final_buffer[i + 1 :]
                                    break
                    else:
                        final_new_lines = final_buffer
                    new_lines_found = final_new_lines
                    break

            # Capture any new log output since the command was sent
            with self._log_lines_lock:
                final_buffer = self._log_lines.copy()
                all_recent_lines = self._log_lines[-10:] if self._log_lines else []

            # If we didn't find new lines in the loop, do a final check
            if not new_lines_found:
                if marker_lines:
                    marker_found = False
                    for i, line in enumerate(final_buffer):
                        if not marker_found:
                            if line == marker_lines[-1]:
                                marker_found = True
                                new_lines_found = final_buffer[i + 1 :]
                                break
                else:
                    new_lines_found = final_buffer

            print(f"DEBUG: Final - Captured {len(new_lines_found)} new lines")

            if new_lines_found:
                print(f"DEBUG: New log lines: {new_lines_found}")
                # Filter and format the response
                response_lines = []
                for line in new_lines_found:
                    line = line.strip()
                    if line:
                        # Clean up log formatting - extract the actual message
                        if "LOG  : General" in line and ">" in line:
                            # Extract message after the timestamp
                            parts = line.split("> ", 2)
                            if len(parts) >= 3:
                                message = parts[2].strip()
                                # Skip the echo of the command itself
                                if not message.startswith("command entered via server console"):
                                    response_lines.append(message)
                            else:
                                response_lines.append(line)
                        else:
                            response_lines.append(line)

                if response_lines:
                    return "\n".join(response_lines)
                else:
                    return f"Command '{command}' sent successfully (no formatted output captured)"
            else:
                return f"Command '{command}' sent successfully (no output captured after {max_wait_time}s)"

        except Exception as e:
            raise ServerControlError(f"Failed to send command '{command}': {e}")

    def get_backup_paths(self) -> Dict[str, pathlib.Path]:
        """
        Get the paths that would be backed up for Project Zomboid.

        Returns:
            Dictionary mapping backup item names to their paths
        """
        user_profile = pathlib.Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
        zomboid_dir = user_profile / "Zomboid"

        return {
            "server_ini": zomboid_dir / "Server" / f"{self.server_name}.ini",
            "sandbox_vars": zomboid_dir / "Server" / f"{self.server_name}_SandboxVars.lua",
            "spawnpoints": zomboid_dir / "Server" / f"{self.server_name}_spawnpoints.lua",
            "spawnregions": zomboid_dir / "Server" / f"{self.server_name}_spawnregions.lua",
            "saves_folder": zomboid_dir / "Saves" / "Multiplayer" / self.server_name,
            "player_database": zomboid_dir / "db" / f"{self.server_name}.db",
        }

    def backup_server(
        self, progress_callback: Optional[Callable[[str], None]] = None
    ) -> BackupResult:
        """
        Create a backup of the Project Zomboid server data.

        Args:
            progress_callback: Optional callback function that receives progress messages

        Returns:
            BackupResult with success status, backup path, and list of files backed up

        Raises:
            ServerControlError: If the server is running or backup fails
        """
        # Don't allow backup while server is running
        if self.is_on():
            raise ServerControlError(
                "Cannot backup while the server is running. Please stop the server first."
            )

        # Friendly names for progress messages
        friendly_names = {
            "server_ini": "server configuration",
            "sandbox_vars": "sandbox settings",
            "spawnpoints": "spawn points",
            "spawnregions": "spawn regions",
            "saves_folder": "world saves",
            "player_database": "player database",
        }

        # Use the backup utility
        backup_utility = BackupUtility(Config.PZ_BACKUP_PATH, self.server_name)
        result = backup_utility.create_backup(
            paths_to_backup=self.get_backup_paths(),
            friendly_names=friendly_names,
            progress_callback=progress_callback,
        )

        # Check if backup failed before cleanup
        if not result.files_backed_up:
            raise ServerControlError(
                f"No files found to backup for server '{self.server_name}'. "
                "Check that the server name is correct and the server has been run at least once."
            )

        # Clean up old backups, keeping only the 6 most recent
        backup_utility.cleanup_old_backups(max_backups=6, progress_callback=progress_callback)

        return result
