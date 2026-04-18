import json
import os
import pathlib
import re
import subprocess
import threading
import time
from collections.abc import Callable
from datetime import datetime

from src.backup_manager import BackupResult, BackupUtility
from src.config import Config
from src.game_server_interface import (
    GameServerManager,
    ServerControlError,
    ServerInfo,
)


class ProjectZomboidServerManager(GameServerManager):
    """Unified Project Zomboid server manager with log-based monitoring."""

    # Version state file name
    VERSION_STATE_FILE = "pz_version_state.json"
    # SteamCMD log file name
    STEAMCMD_LOG_FILE = "steamcmd_output.log"

    def __init__(
        self,
        server_path: pathlib.Path,
        steam_cmd_path: pathlib.Path,
        server_name: str = "servertest",
        memory_gb: int = 4,
    ):
        super().__init__(server_path, steam_cmd_path)
        self._base_server_name = server_name  # Store the base name from config
        self.memory_gb = memory_gb
        self.server_process: subprocess.Popen[str] | None = None
        self._server_started = False
        self._server_info: ServerInfo | None = None
        self._log_lines: list[str] = []
        self._log_lines_lock = threading.Lock()  # Add thread safety for log lines
        self._monitor_thread: threading.Thread | None = None
        self._stop_monitoring = False

    def _get_steamcmd_log_path(self) -> pathlib.Path:
        """Get the path to the SteamCMD log file."""
        # Store in the logs directory if it exists, otherwise in the server directory
        logs_dir = pathlib.Path(__file__).parent.parent / "logs"
        if logs_dir.exists():
            return logs_dir / self.STEAMCMD_LOG_FILE
        server_dir = self.server_path.parent if self.server_path.is_file() else self.server_path
        return server_dir / self.STEAMCMD_LOG_FILE

    def _run_steamcmd(self, cmd: list[str], operation: str = "update") -> str:
        """
        Run a SteamCMD command and log the output to a file.

        Args:
            cmd: The SteamCMD command to run
            operation: Description of the operation for logging

        Returns:
            The stdout from SteamCMD

        Raises:
            subprocess.CalledProcessError: If SteamCMD returns non-zero exit code
        """
        log_path = self._get_steamcmd_log_path()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Log the command being run
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"\n{'=' * 60}\n")
            log_file.write(f"[{timestamp}] SteamCMD {operation}\n")
            log_file.write(f"Command: {' '.join(cmd)}\n")
            log_file.write(f"{'=' * 60}\n\n")

        print(f"Running SteamCMD... (log: {log_path})")

        # Run SteamCMD and capture output
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        # Log stdout and stderr (handle None or non-string values gracefully)
        stdout_text = str(result.stdout) if result.stdout else ""
        stderr_text = str(result.stderr) if result.stderr else ""

        with open(log_path, "a", encoding="utf-8") as log_file:
            if stdout_text:
                log_file.write("--- STDOUT ---\n")
                log_file.write(stdout_text)
                log_file.write("\n")
            if stderr_text:
                log_file.write("--- STDERR ---\n")
                log_file.write(stderr_text)
                log_file.write("\n")
            log_file.write(f"\n[Exit code: {result.returncode}]\n")

        # Check for errors and raise if failed
        if result.returncode != 0:
            print(f"SteamCMD failed! Check log at: {log_path}")

            # Raise a CalledProcessError to maintain compatibility
            error = subprocess.CalledProcessError(
                result.returncode, cmd, result.stdout, result.stderr
            )
            raise error

        return result.stdout

    @property
    def server_name(self) -> str:
        """Get the server name based on the current version branch."""
        current_branch = self._get_current_branch()
        if current_branch == "beta":
            return f"{self._base_server_name}_b42"
        return self._base_server_name

    def _get_version_state_path(self) -> pathlib.Path:
        """Get the path to the version state file."""
        server_dir = self.server_path.parent if self.server_path.is_file() else self.server_path
        return server_dir / self.VERSION_STATE_FILE

    def _get_current_branch(self) -> str:
        """Get the current branch from the state file, defaulting to 'stable'."""
        state_path = self._get_version_state_path()
        if state_path.exists():
            try:
                with open(state_path) as f:
                    state = json.load(f)
                    branch = state.get("current_branch", "stable")
                    return str(branch) if branch else "stable"
            except (json.JSONDecodeError, OSError):
                pass
        return "stable"

    def _save_version_state(self, branch: str) -> None:
        """Save the current branch to the state file."""
        state_path = self._get_version_state_path()
        state = {
            "current_branch": branch,
            "last_updated": datetime.now().isoformat(),
        }
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)

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
                    additional_info = {
                        "steam_port": 16261,
                        "udp_port": 16262,
                        "status": "Running",
                    }
                    break
            elif "port 16261" in line or "port 16262" in line:
                # Fallback for different log formats
                additional_info = {
                    "steam_port": 16261,
                    "udp_port": 16262,
                    "status": "Running",
                }
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
                    print("\nProject Zomboid server has started successfully!")
                    print("-" * 50)

                # Check for shutdown messages
                elif "Saving world" in line or "Server shutdown" in line or "Goodbye" in line:
                    print(f"[SHUTDOWN] {line}")

                # Check for port information
                elif "Server is listening on port" in line:
                    print(f"[NETWORK] {line}")

                # Check for client connection info
                elif "Clients should use" in line:
                    print(f"[INFO] {line}")

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
        Modify the Windows batch file to use custom server name and strip
        unsupported CLI options (e.g. -password, -statistic removed in PZ 42).
        Returns the path to the batch file to use (original or modified).
        Always regenerates the custom batch file to pick up changes.
        """
        # Read the original batch file
        if not batch_file.exists():
            raise ServerControlError(f"Original batch file not found: {batch_file}")

        with open(batch_file) as f:
            content = f.read()

        if "zombie.network.GameServer" not in content:
            raise ServerControlError(
                f"Could not find 'zombie.network.GameServer' in batch file: {batch_file}"
            )

        import re

        # Strip unsupported CLI flags that PZ 42 no longer accepts
        # These appear after zombie.network.GameServer on the java command line
        content = re.sub(r"\s+-password\s+\S+", "", content)
        content = re.sub(r"\s+-statistic\s+\S+", "", content)

        # If using default server name, use original (cleaned) batch file
        if self.server_name == "servertest":
            return batch_file

        custom_batch = batch_file.parent / f"StartServer64_{self.server_name}.bat"

        # Add -servername if not already present
        if f"-servername {self.server_name}" not in content:
            content = content.replace(
                "zombie.network.GameServer",
                f"zombie.network.GameServer -servername {self.server_name}",
            )

        with open(custom_batch, "w") as f:
            f.write(content)

        return custom_batch

    def update_server(self) -> None:
        """Update the Project Zomboid server using SteamCMD for the current branch."""
        if self.is_on():
            raise ServerControlError("Cannot update server while it's running. Stop it first.")

        current_branch = self._get_current_branch()
        cmd = self._build_steamcmd_update_command(current_branch)

        try:
            output = self._run_steamcmd(cmd, operation="update")
            print(f"SteamCMD output: {output}")
        except subprocess.CalledProcessError as error:
            if error.returncode == 10:
                print("Timeout... Please try again.")
            elif error.returncode == 134:
                print("SteamCMD error occurred. Try again.")

            raise ServerControlError(
                f"SteamCMD update failed with exit code {error.returncode}. "
                f"Check log: {self._get_steamcmd_log_path()}"
            ) from error

    def _build_steamcmd_update_command(self, branch: str) -> list[str]:
        """Build the SteamCMD command for updating to a specific branch."""
        server_dir = self.server_path.parent if self.server_path.is_file() else self.server_path
        cmd = [
            str(self.steam_cmd_path),
            "+force_install_dir",
            str(server_dir),
            "+login",
            "anonymous",
            "+app_update",
            "380870",  # Project Zomboid Dedicated Server
        ]

        # Add beta flag if not stable
        if branch == "beta":
            cmd.extend(["-beta", Config.PZ_BETA_BRANCH])

        cmd.extend(["validate", "+quit"])
        return cmd

    def get_version(self) -> dict[str, str]:
        """
        Get the current version/branch information for the server.

        Returns:
            Dictionary with 'branch' (stable/beta), 'server_name', and version info
        """
        current_branch = self._get_current_branch()
        branch_display = "Build 41 (Stable)" if current_branch == "stable" else "Build 42 (Beta)"

        return {
            "branch": current_branch,
            "branch_display": branch_display,
            "server_name": self.server_name,
            "base_server_name": self._base_server_name,
        }

    def set_version(self, branch: str) -> str:
        """
        Switch the server to a different version/branch.

        Args:
            branch: The branch to switch to ('stable', 'b41', 'beta', 'b42')

        Returns:
            A message describing the result of the operation

        Raises:
            ServerControlError: If server is running or update fails
        """
        if self.is_on():
            raise ServerControlError(
                "Cannot switch versions while the server is running. Stop it first."
            )

        # Normalize branch name
        normalized_branch = self._normalize_branch_name(branch)
        current_branch = self._get_current_branch()

        # Check if already on this branch
        if normalized_branch == current_branch:
            branch_display = (
                "Build 41 (Stable)" if normalized_branch == "stable" else "Build 42 (Beta)"
            )
            return (
                f"Server is already on {branch_display}.\n"
                f"Server name: `{self.server_name}`\n"
                "No update needed."
            )

        # Determine old and new server names for messaging
        old_server_name = self.server_name  # Current name before switch
        new_server_name = (
            f"{self._base_server_name}_b42"
            if normalized_branch == "beta"
            else self._base_server_name
        )

        # Check if this is a first-time switch (config doesn't exist yet)
        is_first_time = self._is_first_time_version(normalized_branch)

        # Save the new branch state
        self._save_version_state(normalized_branch)

        # Build and run SteamCMD update
        cmd = self._build_steamcmd_update_command(normalized_branch)

        try:
            output = self._run_steamcmd(cmd, operation=f"version switch to {normalized_branch}")
            print(f"SteamCMD output: {output}")
        except subprocess.CalledProcessError as error:
            # Restore previous state on failure
            self._save_version_state(current_branch)
            log_path = self._get_steamcmd_log_path()
            if error.returncode == 10:
                raise ServerControlError(
                    f"SteamCMD timed out. Please try again. Check log: {log_path}"
                ) from error
            elif error.returncode == 134:
                raise ServerControlError(
                    f"SteamCMD error occurred. Try again. Check log: {log_path}"
                ) from error
            raise ServerControlError(
                f"SteamCMD update failed with exit code {error.returncode}. Check log: {log_path}"
            ) from error

        # Build response message
        branch_display = "Build 41 (Stable)" if normalized_branch == "stable" else "Build 42 (Beta)"
        messages = [
            f"✅ Successfully switched to {branch_display}!",
            f"Server name changed: `{old_server_name}` → `{new_server_name}`",
        ]

        if is_first_time:
            user_profile = pathlib.Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
            config_path = user_profile / "Zomboid" / "Server" / f"{new_server_name}.ini"
            messages.extend(
                [
                    "",
                    "⚠️ **First-time setup for this version!**",
                    "A new server config will be generated on first start.",
                    f"Config location: `{config_path}`",
                    "",
                    "You may want to copy settings (admin password, etc.) from your other config:",
                    f"  `{user_profile / 'Zomboid' / 'Server' / f'{old_server_name}.ini'}`",
                ]
            )

        messages.extend(
            [
                "",
                "📝 **Note:** Saves are independent between versions.",
                "Your progress on each version is preserved separately.",
            ]
        )

        return "\n".join(messages)

    def _normalize_branch_name(self, branch: str) -> str:
        """Normalize branch name to 'stable' or 'beta'."""
        branch_lower = branch.lower().strip()
        if branch_lower in ["stable", "b41"]:
            return "stable"
        elif branch_lower in ["beta", "b42"]:
            return "beta"
        else:
            raise ServerControlError(
                f"Invalid branch '{branch}'. Use 'stable', 'b41', 'beta', or 'b42'."
            )

    def _is_first_time_version(self, branch: str) -> bool:
        """Check if this is the first time switching to this branch (no config exists)."""
        # Determine server name for this branch
        test_server_name = (
            f"{self._base_server_name}_b42" if branch == "beta" else self._base_server_name
        )
        user_profile = pathlib.Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
        config_path = user_profile / "Zomboid" / "Server" / f"{test_server_name}.ini"
        return not config_path.exists()

    def get_available_versions(self) -> list[dict[str, str | bool]]:
        """
        Get the list of available versions/branches for Project Zomboid.

        Returns:
            List of dictionaries with 'id', 'name', 'description', and 'selected' for each version
        """
        current_branch = self._get_current_branch()

        return [
            {
                "id": "stable",
                "name": "Build 41 (Stable)",
                "description": "Current stable release",
                "selected": current_branch == "stable",
            },
            {
                "id": "beta",
                "name": "Build 42 (Beta)",
                "description": f"Unstable beta branch ({Config.PZ_BETA_BRANCH})",
                "selected": current_branch == "beta",
            },
        ]

    def compare_configs(self) -> dict[str, object]:
        """
        Compare the server configurations between stable and beta versions.

        Returns:
            Dictionary containing:
                - 'stable_path': Path to stable config
                - 'beta_path': Path to beta config
                - 'stable_exists': Whether stable config exists
                - 'beta_exists': Whether beta config exists
                - 'differences': List of key differences (if both exist)
                - 'stable_settings': Important settings from stable (if exists)
                - 'beta_settings': Important settings from beta (if exists)
        """
        user_profile = pathlib.Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
        server_dir = user_profile / "Zomboid" / "Server"

        stable_config_path = server_dir / f"{self._base_server_name}.ini"
        beta_config_path = server_dir / f"{self._base_server_name}_b42.ini"

        result: dict[str, object] = {
            "stable_path": str(stable_config_path),
            "beta_path": str(beta_config_path),
            "stable_exists": stable_config_path.exists(),
            "beta_exists": beta_config_path.exists(),
            "differences": [],
            "stable_settings": {},
            "beta_settings": {},
        }

        # Important settings to highlight
        important_keys = [
            "AdminPassword",
            "Password",
            "ServerName",
            "PublicName",
            "MaxPlayers",
            "DefaultPort",
            "UDPPort",
            "SteamPort1",
            "SteamPort2",
            "RCONPort",
            "PVP",
            "PauseEmpty",
            "Open",
            "Public",
            "ServerWelcomeMessage",
            "Mods",
            "Map",
            "WorkshopItems",
        ]

        def parse_ini(path: pathlib.Path) -> dict[str, str]:
            """Parse an INI file and return a dict of key-value pairs."""
            settings: dict[str, str] = {}
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            key, _, value = line.partition("=")
                            settings[key.strip()] = value.strip()
            except (OSError, UnicodeDecodeError):
                pass
            return settings

        # Parse configs if they exist
        stable_settings: dict[str, str] = {}
        beta_settings: dict[str, str] = {}

        if stable_config_path.exists():
            stable_settings = parse_ini(stable_config_path)
            result["stable_settings"] = {
                k: stable_settings.get(k, "<not set>") for k in important_keys
            }

        if beta_config_path.exists():
            beta_settings = parse_ini(beta_config_path)
            result["beta_settings"] = {k: beta_settings.get(k, "<not set>") for k in important_keys}

        # Find differences if both configs exist
        if stable_config_path.exists() and beta_config_path.exists():
            differences: list[dict[str, str]] = []
            for key in important_keys:
                stable_val = stable_settings.get(key, "<not set>")
                beta_val = beta_settings.get(key, "<not set>")
                if stable_val != beta_val:
                    differences.append({"key": key, "stable": stable_val, "beta": beta_val})
            result["differences"] = differences

        return result

    def get_backup_path_for_branch(self, branch: str | None = None) -> pathlib.Path:
        """Get the backup path for a specific branch or the current branch."""
        if branch is None:
            branch = self._get_current_branch()
        return Config.PZ_BACKUP_PATH / branch

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
                marker_lines = self._log_lines[-2:] if self._log_lines else []
                buffer_size_before = len(self._log_lines)

            print(f"DEBUG: Initial buffer size: {buffer_size_before}")
            print(f"DEBUG: Process alive: {self.server_process.poll() is None}")
            print(
                "DEBUG: Monitor thread alive: "
                f"{self._monitor_thread.is_alive() if self._monitor_thread else False}"
            )
            print(f"DEBUG: Marker lines: {marker_lines}")

            # Send the command to the server
            command_to_send = f"{command}\n"
            print(f"Sending command to server: {command}")
            self.server_process.stdin.write(command_to_send)
            self.server_process.stdin.flush()
            print("DEBUG: Command sent and flushed successfully")

            # Wait for the server to process the command and generate output
            max_wait_time = 5.0  # Maximum time to wait for output
            check_interval = 0.1  # Check every 100ms
            waited_time = 0.0
            new_lines_found: list[str] = []

            # Keep checking for new output until we get some or timeout
            while waited_time < max_wait_time:
                time.sleep(check_interval)
                waited_time += check_interval

                # Check for new lines after the marker position
                with self._log_lines_lock:
                    current_buffer = self._log_lines.copy()

                # Find new lines that appeared after our marker
                new_lines_found = []
                if marker_lines:
                    # Find the position of our marker
                    marker_found = False
                    for i, line in enumerate(current_buffer):
                        # Look for the last marker line
                        if not marker_found and line == marker_lines[-1]:
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
                            if not marker_found and line == marker_lines[-1]:
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

            # If we didn't find new lines in the loop, do a final check
            if not new_lines_found:
                if marker_lines:
                    marker_found = False
                    for i, line in enumerate(final_buffer):
                        if not marker_found and line == marker_lines[-1]:
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
                return (
                    f"Command '{command}' sent successfully "
                    f"(no output captured after {max_wait_time}s)"
                )

        except Exception as e:
            raise ServerControlError(f"Failed to send command '{command}': {e}") from e

    def _find_pz_workshop_path(self) -> pathlib.Path:
        if Config.STEAM_PATH is None:
            raise ServerControlError("STEAM_PATH is not configured. Set it in your .env file.")

        vdf_path = Config.STEAM_PATH / "steamapps" / "libraryfolders.vdf"
        if not vdf_path.exists():
            raise ServerControlError(f"Steam library folders file not found: {vdf_path}")

        content = vdf_path.read_text(encoding="utf-8")
        sections = re.split(r'"\d+"\s*\n\s*\{', content)

        for section in sections[1:]:
            if '"108600"' in section:
                path_match = re.search(r'"path"\s+"([^"]+)"', section)
                if path_match:
                    library_path = pathlib.Path(path_match.group(1).replace("\\\\", "\\"))
                    return library_path / "steamapps" / "workshop" / "content" / "108600"

        raise ServerControlError(
            "Project Zomboid (108600) not found in any Steam library. "
            "Make sure the game is installed."
        )

    def _read_workshop_mods(
        self, workshop_content_path: pathlib.Path, workshop_id: str
    ) -> list[tuple[str, list[str]]]:
        mod_folder = workshop_content_path / workshop_id
        if not mod_folder.exists():
            raise ServerControlError(
                f"Workshop item {workshop_id} not found locally. Subscribe to it in Steam first."
            )

        results: list[tuple[str, list[str]]] = []
        seen_ids: set[str] = set()

        for mod_info_path in sorted(mod_folder.rglob("mod.info")):
            try:
                lines = mod_info_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue

            mod_id: str | None = None
            requires: list[str] = []

            for line in lines:
                if line.startswith("id="):
                    mod_id = line[3:].strip()
                elif line.startswith("require="):
                    raw = line[8:].strip()
                    requires = [r.strip().lstrip("\\") for r in raw.split(",") if r.strip()]

            if mod_id and mod_id not in seen_ids:
                seen_ids.add(mod_id)
                results.append((mod_id, requires))

        return results

    def _topological_sort(self, mod_ids: list[str], deps: dict[str, list[str]]) -> list[str]:
        mod_set = set(mod_ids)
        filtered_deps = {m: [d for d in deps.get(m, []) if d in mod_set] for m in mod_ids}

        reverse_deps: dict[str, list[str]] = {m: [] for m in mod_ids}
        in_degree: dict[str, int] = dict.fromkeys(mod_ids, 0)

        for m, reqs in filtered_deps.items():
            for req in reqs:
                reverse_deps[req].append(m)
                in_degree[m] += 1

        ready = sorted(m for m in mod_ids if in_degree[m] == 0)
        result: list[str] = []

        while ready:
            m = ready.pop(0)
            result.append(m)
            for dependent in sorted(reverse_deps[m]):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    ready.append(dependent)
                    ready.sort()

        remaining = sorted(m for m in mod_ids if m not in set(result))
        result.extend(remaining)
        return result

    def _update_ini_mods(self, mods: list[str], workshop_items: list[str]) -> None:
        ini_path = self.get_backup_paths()["server_ini"]
        if not ini_path.exists():
            raise ServerControlError(f"Server ini not found: {ini_path}")

        lines = ini_path.read_text(encoding="utf-8").splitlines(keepends=True)
        new_lines = []
        for line in lines:
            if line.startswith("Mods="):
                new_lines.append("Mods=" + ";".join(mods) + "\n")
            elif line.startswith("WorkshopItems="):
                new_lines.append("WorkshopItems=" + ";".join(workshop_items) + "\n")
            else:
                new_lines.append(line)
        ini_path.write_text("".join(new_lines), encoding="utf-8")

    def set_mods(self, workshop_ids: list[str]) -> str:
        workshop_content_path = self._find_pz_workshop_path()

        all_mod_ids: list[str] = []
        deps: dict[str, list[str]] = {}
        mod_to_workshop: dict[str, str] = {}
        missing: list[str] = []

        for wid in workshop_ids:
            try:
                mods = self._read_workshop_mods(workshop_content_path, wid)
            except ServerControlError:
                missing.append(wid)
                continue

            for mod_id, requires in mods:
                all_mod_ids.append(mod_id)
                deps[mod_id] = requires
                mod_to_workshop[mod_id] = wid

        sorted_mods = self._topological_sort(all_mod_ids, deps)

        seen_workshop_ids: set[str] = set()
        sorted_workshop_ids: list[str] = []
        for mod_id in sorted_mods:
            wid = mod_to_workshop[mod_id]
            if wid not in seen_workshop_ids:
                sorted_workshop_ids.append(wid)
                seen_workshop_ids.add(wid)

        self._update_ini_mods(sorted_mods, sorted_workshop_ids)

        response = (
            f"✅ Updated mod list: {len(sorted_mods)} mods "
            f"from {len(sorted_workshop_ids)} workshop items."
        )
        if missing:
            response += f"\n⚠️ Not found locally (subscribe in Steam first): {', '.join(missing)}"
        return response

    def get_backup_paths(self) -> dict[str, pathlib.Path]:
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

    def backup_server(self, progress_callback: Callable[[str], None] | None = None) -> BackupResult:
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

        # Use version-specific backup path
        backup_path = self.get_backup_path_for_branch()
        backup_utility = BackupUtility(backup_path, self.server_name)
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
