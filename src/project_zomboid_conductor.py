import os
import pathlib
import subprocess

from src.game_server_interface import (
    GameServerConductor,
    GameServerAPI,
    ServerControlError,
)


class ProjectZomboidServerConductor(GameServerConductor):
    """Control a Project Zomboid server."""

    def __init__(
        self,
        server_path: pathlib.Path,
        api: GameServerAPI,
        steam_cmd_path: pathlib.Path,
        server_name: str = "servertest",
        memory_gb: int = 4,
    ):
        super().__init__(server_path, api, steam_cmd_path)
        self.server_name = server_name
        self.memory_gb = memory_gb

    def start_server(self) -> None:
        """Execute the Project Zomboid server and keep it alive."""

        if os.name == "nt":  # Windows
            self._start_windows_server()
        else:  # Linux
            self._start_linux_server()

    def _start_windows_server(self) -> None:
        """Start Project Zomboid server on Windows."""
        # Find the StartServer64.bat file
        server_dir = self.server_path.parent if self.server_path.is_file() else self.server_path

        # Look for the batch file
        batch_files = [
            server_dir / "StartServer64.bat",
            server_dir / "StartServer64_nosteam.bat",
            server_dir / "StartServer32.bat",
        ]

        batch_file = None
        for bf in batch_files:
            if bf.exists():
                batch_file = bf
                break

        if not batch_file:
            raise ServerControlError("Could not find Project Zomboid server batch file")

        # Modify the batch file to use our server name and memory settings
        self._modify_batch_file(batch_file)

        print(f"Starting Project Zomboid server with: {batch_file}")
        self.server_process = subprocess.Popen(
            [str(batch_file)],
            cwd=str(server_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _start_linux_server(self) -> None:
        """Start Project Zomboid server on Linux."""
        server_dir = self.server_path.parent if self.server_path.is_file() else self.server_path
        start_script = server_dir / "start-server.sh"

        if not start_script.exists():
            raise ServerControlError("Could not find start-server.sh")

        start_cmd = ["bash", str(start_script), "-servername", self.server_name]

        print(f"Starting Project Zomboid server with command: {' '.join(start_cmd)}")
        self.server_process = subprocess.Popen(
            start_cmd,
            cwd=str(server_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _modify_batch_file(self, batch_file: pathlib.Path) -> None:
        """Modify the Windows batch file to use custom server name and memory."""
        # This is a simplified approach - in practice, you might want to create
        # a custom batch file or modify the existing one more carefully

        # For now, we'll create a custom batch file
        custom_batch = batch_file.parent / f"StartServer64_{self.server_name}.bat"

        # Create classpath
        classpath_jars = [
            "java/istack-commons-runtime.jar",
            "java/jassimp.jar",
            "java/javacord-2.0.17-shaded.jar",
            "java/javax.activation-api.jar",
            "java/jaxb-api.jar",
            "java/jaxb-runtime.jar",
            "java/lwjgl.jar",
            "java/lwjgl-natives-windows.jar",
            "java/lwjgl-glfw.jar",
            "java/lwjgl-glfw-natives-windows.jar",
            "java/lwjgl-jemalloc.jar",
            "java/lwjgl-jemalloc-natives-windows.jar",
            "java/lwjgl-opengl.jar",
            "java/lwjgl-opengl-natives-windows.jar",
            "java/lwjgl_util.jar",
            "java/sqlite-jdbc-3.27.2.1.jar",
            "java/trove-3.0.3.jar",
            "java/uncommons-maths-1.2.3.jar",
        ]

        java_options = [
            "-Djava.awt.headless=true",
            "-Dzomboid.steam=1",
            "-Dzomboid.znetlog=1",
            "-XX:+UseZGC",
            "-XX:-CreateCoredumpOnCrash",
            "-XX:-OmitStackTraceInFastThrow",
            f"-Xms{self.memory_gb}g",
            f"-Xmx{self.memory_gb}g",
            "-Djava.library.path=natives/;natives/win64/;.",
        ]

        server_args = [
            "zombie.network.GameServer",
            "-servername",
            self.server_name,
            "-statistic",
            "0",
        ]

        java_cmd = f"""@setlocal enableextensions
@cd /d "%~dp0"
SET PZ_CLASSPATH={";".join(classpath_jars)}

".\\jre64\\bin\\java.exe" {" ".join(java_options)} -cp %PZ_CLASSPATH% {" ".join(server_args)}
PAUSE"""

        with open(custom_batch, "w") as f:
            f.write(java_cmd)

    def update_server(self) -> None:
        """Update the Project Zomboid server using SteamCMD."""

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
